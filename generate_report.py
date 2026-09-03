# -*- coding: utf-8 -*-
"""
generate_report.py
고객 정보 + 상품 종류(product_id)를 받으면 끝까지 자동으로 처리하는 파이프라인.

사용법:
  python3 generate_report.py
"""

import os
import uuid
from saju_core import calculate_saju, calculate_period_pillars, calculate_year_all_months
from report_prompts import (
    build_section_prompt, build_profile_kernel_prompt, PRODUCTS_BY_ID, SECTION_SPECS
)
from build_report import build_report

# ---------------------------------------------------------------------------
# AI 호출 부분
# ---------------------------------------------------------------------------

def call_ai_for_section(prompt: str) -> str:
    """실제 Anthropic API를 호출해서 해석문을 생성한다."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
            "https://console.anthropic.com 에서 API 키를 발급받아 설정하세요."
        )

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# 전체 파이프라인
# ---------------------------------------------------------------------------

def generate_full_report(customer: dict, product_id: str = "full",
                          sections_override: dict = None, output_dir: str = ".",
                          watermark: bool = False, order_id=None) -> str:
    """
    customer: {
        "name", "phone", "email",
        "birth_year", "birth_month", "birth_day", "birth_hour", "birth_minute",
        "gender": "M"/"F", "is_lunar": bool(현재 미지원)
    }
    product_id: report_prompts.PRODUCTS 중 하나의 id (예: "full", "new_year", "love" ...)
    sections_override: 테스트용으로 미리 써둔 해석문을 넣고 싶을 때 사용 (AI 호출 생략)
    watermark: True면 'SAMPLE · 미리보기' 워터마크가 찍힌 샘플본으로 생성
               (결제 없이 테스트/미리보기 용도로 보낼 때 사용)
    order_id: 파일명을 동명이인/동시처리 주문끼리도 겹치지 않게 만들기 위한 고유값.
              없으면(테스트 발송 등) 임의의 고유값을 대신 생성한다.

    반환값: 생성된 PDF 파일 경로
    """
    if customer.get("is_lunar"):
        raise NotImplementedError("음력 입력은 아직 지원하지 않습니다 (알려진 한계).")

    if product_id not in PRODUCTS_BY_ID:
        raise ValueError(f"알 수 없는 상품 ID: {product_id}")
    product = PRODUCTS_BY_ID[product_id]
    section_keys = product["sections"]

    # 1) 계산 -----------------------------------------------------------
    data = calculate_saju(
        customer["birth_year"], customer["birth_month"], customer["birth_day"],
        customer["birth_hour"], customer.get("birth_minute", 0),
        gender=customer["gender"]
    )

    # 신년운세/월간운세처럼 '지금 시점' 데이터가 필요한 상품을 위해 미리 계산
    period = calculate_period_pillars()
    # '향후 5년 흐름' 섹션을 위해, 올해부터 5년치 세운을 미리 계산해둔다
    current_year = period["year"]
    period_list = [calculate_period_pillars(current_year + i, 1, 1) for i in range(5)]
    # '달마다 보는 올해 흐름' 섹션을 위해, 올해 1~12월 전체 월운을 미리 계산해둔다
    months_data = calculate_year_all_months(current_year)

    # 2) AI 해석문 생성 ---------------------------------------------------
    if sections_override:
        sections = sections_override
    else:
        # 2-1) 핵심 프로필(인물 설정표)을 먼저 딱 한 번 생성
        kernel_prompt = build_profile_kernel_prompt(data)
        profile_kernel = call_ai_for_section(kernel_prompt)

        # 2-2) 상품에 포함된 섹션만 순서대로 생성 (일관성 유지 로직 포함)
        sections = {}
        written_so_far = []
        total = len(section_keys)
        for i, key in enumerate(section_keys, 1):
            spec = SECTION_SPECS[key]
            if spec.get("is_static"):
                # 용어해설처럼 고정된 설명은 AI 호출 없이 그대로 사용 (정확성 + 비용 절감)
                sections[key] = spec["static_content"]
                print(f"  ({i}/{total}) {key} - 고정 텍스트 사용")
                continue

            print(f"  ({i}/{total}) {key} 섹션 생성 중...")
            prior_summary = "\n".join(written_so_far) if written_so_far else None
            prompt = build_section_prompt(
                key, data,
                profile_kernel=profile_kernel,
                prior_sections_summary=prior_summary,
                period=period,
                period_list=period_list,
                months_data=months_data,
            )
            text = call_ai_for_section(prompt)
            sections[key] = text
            written_so_far.append(f"[{key}] {text[:120]}...")
            print(f"  ({i}/{total}) {key} 완료")

    # 3) PDF 조립 ---------------------------------------------------------
    # order_id(또는 임의의 고유값)를 파일명에 넣어, 동명이인이거나 여러 주문이
    # 동시에 처리될 때 서로 다른 고객의 PDF 파일이 같은 경로로 덮어써지는 것을 방지한다.
    safe_name = customer["name"].replace(" ", "_")
    sample_tag = "_SAMPLE" if watermark else ""
    unique_id = str(order_id) if order_id is not None else uuid.uuid4().hex[:8]
    output_pdf = os.path.join(output_dir, f"saju_report_{unique_id}_{safe_name}_{product_id}{sample_tag}.pdf")

    birth_info = (
        f"{customer['birth_year']}년 {customer['birth_month']}월 {customer['birth_day']}일 "
        f"{customer['birth_hour']}시 {customer.get('birth_minute', 0)}분생 · 양력 · "
        f"{'남' if customer['gender']=='M' else '여'}"
    )

    build_report(
        data,
        name=customer["name"],
        birth_info=birth_info,
        sections=sections,
        section_order=section_keys,
        product_name=product["name"],
        output_pdf=output_pdf,
        watermark=watermark,
    )

    return output_pdf


if __name__ == "__main__":
    customer = {
        "name": "김민지", "phone": "010-1234-5678", "email": "example@email.com",
        "birth_year": 1995, "birth_month": 8, "birth_day": 22,
        "birth_hour": 15, "birth_minute": 45, "gender": "F",
    }

    # 데모용 - AI 호출 없이 상품별로 섹션 개수만 다르게 나오는지 구조 검증
    demo_sections_full = {
        "총론": "총론 테스트 문단입니다.\n\n두번째 문단입니다.",
        "성격": "성격 테스트 문단입니다.\n\n두번째 문단입니다.",
        "대운흐름": "대운 테스트 문단입니다.\n\n두번째 문단입니다.",
        "재물운": "재물 테스트 문단입니다.",
        "애정운": "애정 테스트 문단입니다.",
        "건강운": "건강 테스트 문단입니다.",
    }
    p1 = generate_full_report(customer, product_id="full", sections_override=demo_sections_full)
    print("종합 리포트:", p1)

    demo_sections_love = {
        "성격": "연애 관점 성격 테스트 문단입니다.",
        "애정운": "애정운 상세 테스트 문단입니다.",
    }
    p2 = generate_full_report(customer, product_id="love", sections_override=demo_sections_love)
    print("연애운세:", p2)
