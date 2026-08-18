# -*- coding: utf-8 -*-
"""
notify.py — 완성된 PDF를 이메일과 카카오 알림톡으로 발송하는 모듈.

이메일: smtplib로 완전히 동작하는 코드 (SMTP 계정만 있으면 바로 됨)
카카오 알림톡: 카카오의 공식 비즈니스 API는 직접 붙이기 복잡해서,
              솔라피(Solapi)·알리고 같은 '알림톡 대행 API' 사용을 권장.
              (소규모 사업자가 가장 흔히 쓰는 방식 — 카카오 채널 등록 +
              알림톡 템플릿 사전 심사만 하면, 이후엔 REST API 호출 한 줄로 발송 가능)
"""

import os
import socket
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ---------------------------------------------------------------------------
# 일부 호스팅 환경(Railway 등)은 컨테이너에 IPv6 라우팅이 안 되어 있는데,
# smtplib이 IPv6 주소로 먼저 접속을 시도하다가 "Network is unreachable"
# 오류가 나는 경우가 있다. 아래는 이 프로세스의 모든 소켓 연결을
# IPv4로만 하도록 강제하는 처리이다 (이 앱은 IPv6가 딱히 필요하지 않다).
# ---------------------------------------------------------------------------
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _ipv4_only_getaddrinfo

# ---------------------------------------------------------------------------
# 이메일 발송 (완전히 동작하는 코드 — 환경변수만 채우면 됨)
# ---------------------------------------------------------------------------

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SENDER_NAME = os.environ.get("SENDER_NAME", "사주 명식 리포트")


def send_email_with_pdf(to_email: str, name: str, pdf_path: str):
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER / SMTP_PASS 환경변수가 설정되지 않았습니다.")

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = f"[사주 명식 리포트] {name}님의 리포트가 도착했습니다"

    body = f"""{name}님, 안녕하세요.

신청하신 사주 명식 리포트가 완성되어 첨부파일로 보내드립니다.
PDF 파일을 열어 확인해주세요.

감사합니다.
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
    msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# 카카오 알림톡 발송
#
# 아래는 '솔라피(Solapi)' API 기준 예시 코드다. 실제 사용 전 준비물:
#   1. 카카오 비즈니스채널 개설 (https://business.kakao.com)
#   2. 솔라피 등 알림톡 대행사에 발신 프로필 등록 + 채널 연동
#   3. 알림톡 템플릿 작성 후 카카오 사전 심사 통과 (보통 1~2일 소요)
#      - 템플릿 예시: "#{고객명}님, 사주 명식 리포트가 도착했어요! 아래 링크에서
#        확인해보세요. #{다운로드링크}"
#   4. 승인된 템플릿 코드를 아래 ALIMTALK_TEMPLATE_ID에 입력
#
# 알림톡은 파일 첨부가 안 되므로(카카오 정책), PDF를 서버에 올려두고
# '다운로드 링크'를 알림톡 메시지에 넣어 보내는 방식이 표준이다.
# 발송 실패 시(예: 상대가 카카오톡 미사용자) 문자(SMS)로 대체 발송하는
# '대체발송' 옵션도 대행사 API가 보통 지원한다.
# ---------------------------------------------------------------------------

SOLAPI_API_KEY = os.environ.get("SOLAPI_API_KEY")
SOLAPI_API_SECRET = os.environ.get("SOLAPI_API_SECRET")
KAKAO_SENDER_KEY = os.environ.get("KAKAO_SENDER_KEY")  # 카카오 발신프로필 키
ALIMTALK_TEMPLATE_ID = os.environ.get("ALIMTALK_TEMPLATE_ID")
PUBLIC_PDF_BASE_URL = os.environ.get("PUBLIC_PDF_BASE_URL", "https://YOUR_SERVER_DOMAIN/files")


def send_kakao_alimtalk(to_phone: str, name: str, pdf_filename: str):
    if not (SOLAPI_API_KEY and SOLAPI_API_SECRET and KAKAO_SENDER_KEY and ALIMTALK_TEMPLATE_ID):
        raise RuntimeError(
            "카카오 알림톡 발송에 필요한 환경변수가 설정되지 않았습니다. "
            "(SOLAPI_API_KEY, SOLAPI_API_SECRET, KAKAO_SENDER_KEY, ALIMTALK_TEMPLATE_ID) "
            "설정 전까지는 이메일 발송만 동작합니다."
        )

    download_link = f"{PUBLIC_PDF_BASE_URL}/{pdf_filename}"

    # 솔라피 API 인증은 HMAC 서명 방식이다. 아래는 개념 설명용 단순화된 형태이며,
    # 실제 연동시 솔라피 공식 SDK(pip install solapi) 사용을 강력히 권장한다.
    payload = {
        "message": {
            "to": to_phone.replace("-", ""),
            "from": os.environ.get("SENDER_PHONE", ""),  # 사업자 발신번호
            "kakaoOptions": {
                "pfId": KAKAO_SENDER_KEY,
                "templateId": ALIMTALK_TEMPLATE_ID,
                "variables": {
                    "#{고객명}": name,
                    "#{다운로드링크}": download_link,
                },
                "disableSms": False,  # True로 하면 알림톡 실패시 문자 대체발송 안 함
            }
        }
    }

    # 실제 요청 (솔라피 SDK 사용시 이 부분이 훨씬 간단해진다)
    resp = requests.post(
        "https://api.solapi.com/messages/v4/send",
        json=payload,
        headers={"Authorization": f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}"},  # 실제로는 서명 필요
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
