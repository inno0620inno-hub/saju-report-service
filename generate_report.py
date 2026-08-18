# -*- coding: utf-8 -*-
"""
generate_report.py
고객 정보(이름/연락처/이메일/생년월일시) 하나만 넣으면 끝까지 자동으로 처리하는
전체 파이프라인의 진입점.

실제 운영 환경에서 필요한 것:
1. 이 스크립트가 서버(예: FastAPI/Flask)에서 폼 제출을 받으면 바로 호출됨
2. call_ai_for_section()이 실제 Claude API를 호출하도록 연결 (지금은 자리만 마련)
3. 완성된 PDF를 카카오 알림톡/이메일로 발송하는 코드 추가 (다음 단계)

사용법:
  python3 generate_report.py
  (하단 __main__ 부분의 customer 딕셔너리를 실제 폼 데이터로 교체하면 됨)
"""

import os
from saju_core import calculate_saju
from report_prompts import build_section_prompt, build_profile_kernel_prompt
from build_report import build_report

# ---------------------------------------------------------------------------
# AI 호출 부분 (실제 배포시 여기를 Claude API 호출로 교체)
# ---------------------------------------------------------------------------

def call_ai_for_section(prompt: str) -> str:
    """
    실제 Anthropic API를 호출해서 해석문을 생성한다.
    환경변수 ANTHROPIC_API_KEY가 설정되어 있어야 한다.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
            "https://console.anthropic.com 에서 API 키를 발급받아 설정하세요."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# 전체 파이프라인
# ---------------------------------------------------------------------------

def generate_full_report(customer: dict, sections_override: dict = None,
                          output_dir: str = ".") -> str:
    """
    customer: {
        "name": str, "phone": str, "email": str,
        "birth_year": int, "birth_month": int, "birth_day": int,
        "birth_hour": int, "birth_minute": int,
        "gender": "M" or "F",
        "is_lunar": bool (현재 미지원, True면 에러),
    }
    sections_override: 이미 생성된 해석문이 있으면 여기 넣어서 AI 호출을 건너뛴다.
                        (지금 데모에서는 이 방식을 사용)

    반환값: 생성된 PDF 파일 경로
    """
    if customer.get("is_lunar"):
        raise NotImplementedError("음력 입력은 아직 지원하지 않습니다 (알려진 한계).")

    # 1) 계산 -----------------------------------------------------------
    data = calculate_saju(
        customer["birth_year"], customer["birth_month"], customer["birth_day"],
        customer["birth_hour"], customer.get("birth_minute", 0),
        gender=customer["gender"]
    )

    # 2) AI 해석문 생성 ---------------------------------------------------
    section_names = ["총론", "성격", "대운흐름", "재물운", "애정운", "건강운"]
    if sections_override:
        sections = sections_override
    else:
        # 2-1) 핵심 프로필(인물 설정표)을 먼저 딱 한 번 생성 -> 이후 모든 섹션이
        #      이 설정을 공유해서 서로 모순되지 않게 만든다.
        kernel_prompt = build_profile_kernel_prompt(data)
        profile_kernel = call_ai_for_section(kernel_prompt)

        # 2-2) 섹션을 순서대로 생성하면서, 매번 (a) 고정된 프로필 (b) 지금까지
        #      쓴 섹션들의 요약을 함께 넘겨서 뒤로 갈수록 일관성이 유지되게 한다.
        sections = {}
        written_so_far = []
        for name in section_names:
            prior_summary = "\n".join(written_so_far) if written_so_far else None
            prompt = build_section_prompt(
                name, data,
                profile_kernel=profile_kernel,
                prior_sections_summary=prior_summary,
            )
            text = call_ai_for_section(prompt)
            sections[name] = text
            # 다음 섹션을 위해, 방금 쓴 섹션의 핵심만 한두 문장으로 압축해 누적
            written_so_far.append(f"[{name}] {text[:120]}...")

    # build_report.py의 키 이름과 맞춤 (총론/성격/대운흐름/재물운/애정운/건강운)
    sections_for_pdf = {
        "총론": sections["총론"],
        "성격": sections["성격"],
        "대운흐름": sections["대운흐름"],
        "재물운": sections["재물운"],
        "애정운": sections["애정운"],
        "건강운": sections["건강운"],
    }

    # 3) PDF 조립 ---------------------------------------------------------
    safe_name = customer["name"].replace(" ", "_")
    output_pdf = os.path.join(output_dir, f"saju_report_{safe_name}.pdf")

    birth_info = (
        f"{customer['birth_year']}년 {customer['birth_month']}월 {customer['birth_day']}일 "
        f"{customer['birth_hour']}시 {customer.get('birth_minute', 0)}분생 · 양력 · "
        f"{'남' if customer['gender']=='M' else '여'}"
    )

    build_report(
        data,
        name=customer["name"],
        birth_info=birth_info,
        sections=sections_for_pdf,
        output_pdf=output_pdf,
    )

    # 4) (다음 단계) 카카오/이메일 발송 -------------------------------------
    # send_via_kakao(customer["phone"], output_pdf)
    # send_via_email(customer["email"], output_pdf)

    return output_pdf


if __name__ == "__main__":
    # ===== 실제 폼 제출로 들어왔다고 가정한 새 고객 데이터 =====
    customer = {
        "name": "김민지",
        "phone": "010-1234-5678",
        "email": "example@email.com",
        "birth_year": 1995, "birth_month": 8, "birth_day": 22,
        "birth_hour": 15, "birth_minute": 45,
        "gender": "F",
    }

    # AI API가 아직 연결 안 되어 있으므로, 이 데모에서는 해석문을 미리 준비해서 넣는다.
    # (실제 배포시엔 이 부분을 통째로 지우고 sections_override=None으로 호출하면
    #  call_ai_for_section이 자동으로 Claude API를 호출한다.)
    demo_sections = {
        "총론": """이 사주는 을해년 갑신월 무진일 신유시로, 흙(土)과 금(金)이 서로를 도와가며
단단한 짜임새를 만드는 구성입니다. 오행 중 금(金)이 세 자리로 가장 강하고, 토(土)도
두 자리를 차지해 안정과 결단력을 동시에 갖춘 사주입니다.

본인을 상징하는 일간은 무토(戊土)입니다. 무토는 넓은 들판이나 큰 산 같은 흙으로,
쉽게 흔들리지 않는 묵직함이 특징입니다. 여기에 금 기운이 강하게 실려 있어, 겉으로는
차분하지만 속으로는 예리하게 판단하고 정리하는 힘을 가진 사람입니다.

다만 목(木)과 화(火)의 기운이 상대적으로 약해서, 새로운 것을 벌이거나 감정을 밖으로
표현하는 데는 다소 신중한 편입니다. 스스로 판단이 서기 전까지는 잘 움직이지 않는
타입이라, 주변에서는 가끔 답답하게 느낄 수도 있습니다.""",

        "성격": """무토 일간에 금 기운이 두터운 이 사람은, 한번 결정한 것은 좀처럼 바꾸지 않는
확고함을 가지고 있습니다. 신중하게 판단하고 나면 그 뒤로는 흔들림 없이 밀고
나가는 뚝심이 강점입니다.

강점을 꼽자면 첫째, 정리와 판단력입니다. 금 기운이 강한 만큼 복잡한 상황에서도
핵심을 빠르게 골라내는 힘이 있습니다. 둘째, 신뢰감입니다. 무토 특유의 안정감으로
주변 사람들에게 "저 사람은 믿을 수 있다"는 인상을 줍니다. 셋째, 자기 관리입니다.
스스로 세운 기준과 원칙을 잘 지키는 편입니다.

보완하면 좋을 점은, 우선 유연성입니다. 한번 정한 방식을 고수하려는 경향이 강해서,
상황이 바뀌었을 때 전환이 늦을 수 있습니다. 의식적으로 "다른 방법도 있을 수 있다"는
여지를 남겨두는 연습이 도움이 됩니다. 또 감정 표현도 조금 더 적극적으로 해보는 것이
관계를 더 풍성하게 만들어줄 수 있습니다.""",

        "대운흐름": """대운의 방향과 흐름은 이 사주가 앞으로 어떤 시기에 어떤 색깔을 띠는지 보여줍니다.
초반 대운은 기초를 다지는 시기로, 무토 일간의 안정감이 학업과 자기 관리 능력으로
발현됩니다.

이후 이어지는 대운에서는 금 기운이 한층 강화되면서, 전문성을 쌓고 스스로의 영역을
확실히 구축하는 흐름이 두드러집니다. 이 시기엔 성급하게 넓히기보다 한 분야를
깊이 파는 전략이 훨씬 유리합니다.

중반 이후로는 목(木) 기운이 서서히 들어오면서, 그동안 다져온 실력을 바탕으로
새로운 확장과 도전을 시도할 수 있는 타이밍이 열립니다. 이 흐름이 다가올 때
미리 준비해두면 도약의 발판으로 삼을 수 있습니다.""",

        "재물운": """이 사주는 계획적이고 신중하게 재물을 쌓아가는 유형입니다. 금 기운이 강한
만큼, 숫자와 계획에 밝고 위험한 곳에 무리하게 베팅하기보다 안정적인 축적을
선호하는 경향이 있습니다.

토(土)의 안정감과 금(金)의 결단력이 만나, 한번 정한 저축·투자 계획은 꾸준히
지켜나가는 힘이 있습니다. 다만 지나치게 신중한 나머지 좋은 기회를 놓칠 수 있으니,
이미 충분히 검토한 사안이라면 실행에 옮기는 결단도 필요합니다.""",

        "애정운": """신중하고 진중한 만큼, 연애에서도 쉽게 마음을 열지 않지만 한번 신뢰를 쌓으면
매우 안정적이고 오래가는 관계를 만드는 타입입니다.

이 사주와 잘 맞는 상대는 서두르지 않고 천천히 다가와주는 사람입니다. 성급하게
관계를 재촉하기보다, 충분한 시간을 두고 신뢰를 쌓아가는 만남에서 훨씬 편안함을
느낍니다. 목(木) 기운이 들어오는 시기부터 관계에서 좀 더 적극적이고 표현이
풍부해지는 흐름을 보입니다.""",

        "건강운": """오행 중 목(木)과 화(火)가 상대적으로 약한 구조라, 몸에서는 이 기운이 담당하는
부위 — 간, 근육, 그리고 혈액순환 — 에 평소 신경을 쓰면 좋습니다. 스트레칭이나
가벼운 유산소 운동을 꾸준히 챙기는 것이 이 사주의 균형에 도움이 됩니다.

금 기운이 강한 사주 특성상 호흡기나 피부 쪽에 예민함이 나타날 수 있으니, 건조한
환경을 피하고 충분한 수분 섭취와 휴식을 챙기는 습관을 추천합니다.""",
    }

    output_path = generate_full_report(customer, sections_override=demo_sections)
    print(f"\n완성된 리포트: {output_path}")
