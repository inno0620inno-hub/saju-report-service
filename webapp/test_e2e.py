# -*- coding: utf-8 -*-
"""
test_e2e.py — 배포된 서버에 대해 실제 신청부터 PDF 다운로드/검증까지
전체 플로우를 자동으로 확인하는 end-to-end 테스트 스크립트.

흐름:
  1. POST /api/submit 으로 연애운세(product_id="love") 즉시발송 신청
  2. POST /admin/confirm/{order_id} 로 관리자 입금확인 처리 (HTTP Basic 인증)
  3. GET /api/orders/{order_id} 를 10초 간격, 최대 5분간 폴링해서 처리 완료 대기
  4. status가 'sent'가 되면 /files/{pdf_filename} 에서 실제 PDF 다운로드
  5. pdfplumber로 텍스트를 추출해서, 문단이 문장부호 없이 뚝 끊긴 곳이 있는지 검사
  6. 결과 요약 출력

사용법:
  python3 test_e2e.py

필요 조건:
  - webapp/.env 에 ADMIN_USERNAME, ADMIN_PASSWORD가 대상 서버(BASE_URL)의
    관리자 계정과 동일하게 설정되어 있어야 한다.
  - pip install pdfplumber (requirements.txt에 포함됨)
"""

import os
import re
import sys
import time

import requests
import pdfplumber
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

BASE_URL = "https://saju-report-service-production.up.railway.app"
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

POLL_INTERVAL_SEC = 10
MAX_WAIT_SEC = 300

# 실제로 이메일을 받아볼 수 있는 주소로 바꾸고 싶으면 아래 email 값만 수정하면 된다.
TEST_CUSTOMER = {
    "name": "이지은",
    "phone": "010-1234-5678",
    "email": "test@example.com",
    "birth_date": "1995-08-22",
    "birth_time": "15:45",
    "time_unknown": False,
    "gender": "F",
    "product_id": "love",
    "delivery_mode": "immediate",
}

# 문단이 이 문자들 중 하나로 끝나면 정상 종결로 간주한다 (닫는 괄호/따옴표까지 고려).
SENTENCE_END_CHARS = (".", "!", "?", "…", "”", '"', "'", ")")

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "e2e_test_output")


def submit_order():
    print(f"[1/5] POST /api/submit ({TEST_CUSTOMER['product_id']} 상품, {TEST_CUSTOMER['name']})")
    resp = requests.post(f"{BASE_URL}/api/submit", json=TEST_CUSTOMER, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"신청 실패: HTTP {resp.status_code} - {resp.text}")
    data = resp.json()
    order_id = data["order_id"]
    print(f"      -> order_id={order_id}, status={data['status']}")
    return order_id


def confirm_payment(order_id):
    if not (ADMIN_USERNAME and ADMIN_PASSWORD):
        raise RuntimeError(
            "ADMIN_USERNAME / ADMIN_PASSWORD가 .env에 설정되어 있지 않습니다."
        )
    print(f"[2/5] POST /admin/confirm/{order_id} (관리자 인증)")
    resp = requests.post(
        f"{BASE_URL}/admin/confirm/{order_id}",
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD),
        timeout=30,
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "입금확인 실패: 401 Unauthorized - .env의 ADMIN_USERNAME/ADMIN_PASSWORD가 "
            "실제 배포 서버의 관리자 계정과 다릅니다."
        )
    if resp.status_code != 200:
        raise RuntimeError(f"입금확인 실패: HTTP {resp.status_code} - {resp.text}")
    print("      -> 입금확인 처리 완료, 서버가 리포트 생성을 시작합니다")


def wait_for_completion(order_id):
    print(f"[3/5] GET /api/orders/{order_id} 를 {POLL_INTERVAL_SEC}초 간격, "
          f"최대 {MAX_WAIT_SEC}초 폴링")
    elapsed = 0
    while elapsed <= MAX_WAIT_SEC:
        resp = requests.get(f"{BASE_URL}/api/orders/{order_id}", timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"주문 조회 실패: HTTP {resp.status_code} - {resp.text}")
        order = resp.json()
        status = order["status"]
        print(f"      [{elapsed:>3}s] status={status}")
        if status in ("sent", "failed"):
            return order
        time.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC
    raise TimeoutError(
        f"{MAX_WAIT_SEC}초 안에 처리가 끝나지 않았습니다 (마지막 status={status})"
    )


def download_pdf(order):
    pdf_path = order.get("pdf_path")
    if not pdf_path:
        raise RuntimeError("주문에 pdf_path가 없습니다.")
    filename = os.path.basename(pdf_path)
    url = f"{BASE_URL}/files/{filename}"
    print(f"[4/5] GET {url}")
    resp = requests.get(url, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"PDF 다운로드 실패: HTTP {resp.status_code}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    local_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(resp.content)
    print(f"      -> 저장됨: {local_path} ({len(resp.content):,} bytes)")
    return local_path


def check_truncated_paragraphs(pdf_path):
    print(f"[5/5] PDF 텍스트 추출 및 문단 종결 검사: {pdf_path}")

    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")
    full_text = "\n\n".join(pages_text)

    # 빈 줄로 구분된 블록을 문단 후보로 본다. 챕터 제목/페이지 번호/목차 같은
    # 짧은 라벨은 문장이 아니므로 최소 길이 기준으로 걸러낸다.
    MIN_PARAGRAPH_LEN = 40
    raw_blocks = re.split(r"\n\s*\n", full_text)
    paragraphs = [b.strip() for b in raw_blocks if len(b.strip()) >= MIN_PARAGRAPH_LEN]

    truncated = [p for p in paragraphs if not p.rstrip().endswith(SENTENCE_END_CHARS)]

    print(f"      검사한 문단 후보: {len(paragraphs)}개")
    if truncated:
        print(f"      ⚠️ 잘린 것 같은 문단 발견: {len(truncated)}개")
        for p in truncated:
            tail = p[-100:].replace("\n", " ")
            print(f"         ...{tail}")
    else:
        print("      ✅ 잘린 문단 없음 (모든 문단이 문장부호로 끝남)")

    return truncated


def main():
    print(f"=== E2E 테스트 시작: {BASE_URL} ===\n")

    result = {
        "order_id": None,
        "final_status": None,
        "pdf_downloaded": False,
        "truncated_paragraphs": None,
        "error": None,
    }

    try:
        order_id = submit_order()
        result["order_id"] = order_id

        confirm_payment(order_id)

        order = wait_for_completion(order_id)
        result["final_status"] = order["status"]

        if order["status"] == "failed":
            result["error"] = order.get("error_message", "(에러 메시지 없음)")
        elif order["status"] == "sent":
            local_pdf = download_pdf(order)
            result["pdf_downloaded"] = True
            result["truncated_paragraphs"] = check_truncated_paragraphs(local_pdf)

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ 테스트 중 예외 발생: {e}")

    print("\n=== 결과 요약 ===")
    print(f"order_id       : {result['order_id']}")
    print(f"최종 status    : {result['final_status']}")
    print(f"PDF 다운로드   : {'성공' if result['pdf_downloaded'] else '실패/건너뜀'}")
    if result["truncated_paragraphs"] is not None:
        n = len(result["truncated_paragraphs"])
        print(f"잘린 문단 검사 : {'⚠️ ' + str(n) + '개 발견' if n else '✅ 없음'}")
    if result["error"]:
        print(f"에러/실패 사유 : {result['error']}")

    overall_ok = (
        result["final_status"] == "sent"
        and result["pdf_downloaded"]
        and not result["truncated_paragraphs"]
    )
    print(f"\n전체 결과: {'✅ PASS' if overall_ok else '❌ FAIL'}")
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
