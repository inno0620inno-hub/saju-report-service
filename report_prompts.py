# -*- coding: utf-8 -*-
"""
report_prompts.py
saju_core.calculate_saju()의 계산 결과(순수 데이터)를 받아서,
AI가 각 리포트 섹션의 해석문을 생성할 때 쓸 '구조화된 프롬프트'를 만든다.

이 버전의 핵심 변화: 섹션들을 '레고 블록'처럼 만들어서, 상품(PRODUCTS)마다
필요한 섹션만 골라 조합할 수 있게 했다. 새 상품을 추가하고 싶으면
PRODUCTS 리스트에 항목만 추가하면 된다 (섹션이 이미 있는 경우).
"""

COMMON_STYLE_GUIDE = """
[문체 가이드]
- 따뜻하고 신뢰감 있는 전문가 톤. 그러나 지나치게 확정적인 단언("반드시 ~된다", "100% ~하다")은
  피하고 "~한 경향이 있다", "~할 가능성이 높다", "~에 유리한 시기다" 같은 참고형 어조를 쓴다.
- 추상적인 명리학 용어(십신, 용신 등)를 그대로 나열하지 말고, 독자가 이해할 수 있는
  일상적인 언어로 풀어서 설명한다.
- 각 섹션은 "이 사주는 이렇다 -> 그래서 실생활에서 이런 모습으로 나타난다 -> 이럴 때 이렇게
  하면 좋다"의 흐름으로 쓴다. 단순 특징 나열이 아니라 실용적 조언까지 이어지게 한다.
- 건강운은 특정 질병을 단정하지 않고 "관리가 필요한 부분" 수준으로 표현한다 (의료 오인 방지).
- 재물운은 특정 투자처를 추천하지 않는다 (금융 오인 방지).
"""


def _format_pillars(data):
    y, m, d, h = data["year_pillar"], data["month_pillar"], data["day_pillar"], data["hour_pillar"]
    return f"""
- 연주(年柱): {y['str']}({y['hanja']}) - 천간 {y['gan']}({y['gan_oheng']}/{y['umyang']}), 지지 {y['ji']}({y['ji_oheng']})
- 월주(月柱): {m['str']}({m['hanja']}) - 천간 {m['gan']}({m['gan_oheng']}/{m['umyang']}), 지지 {m['ji']}({m['ji_oheng']})
- 일주(日柱): {d['str']}({d['hanja']}) - 천간 {d['gan']}({d['gan_oheng']}/{d['umyang']}), 지지 {d['ji']}({d['ji_oheng']})  [일간=본인]
- 시주(時柱): {h['str']}({h['hanja']}) - 천간 {h['gan']}({h['gan_oheng']}/{h['umyang']}), 지지 {h['ji']}({h['ji_oheng']})
- 오행 분포: {data['oheng_distribution']}
- 일간(본인을 상징하는 글자): {data['day_master']}
""".strip()


def build_profile_kernel_prompt(data):
    pillars_text = _format_pillars(data)
    return f"""
아래 사주 데이터를 바탕으로, 이후 여러 섹션(성격/재물운/애정운/건강운/대운흐름 등)을
작성할 때 계속 참조할 '핵심 설정 카드'를 만들어라. 이건 최종 소비자에게 보여줄
문서가 아니라, 이후 작성 작업의 기준이 될 내부 설정표다.

[사주 원국 데이터]
{pillars_text}

[요청] 아래 항목만 짧고 명확하게 채워라. 각 항목은 한두 문장, 리스트는 3개 이내.
- 핵심 기질 키워드 (3개, 예: "신중함", "포용력", "현실감각")
- 강점 (2개)
- 보완점 (2개, 부정적으로 단정하지 말고 '~에 신경쓰면 좋다' 톤)
- 재물 성향 한 줄 (예: "안정 추구형" / "활동을 통해 버는 유형" 등)
- 애정 성향 한 줄 (예: "천천히 마음을 여는 타입" 등)
- 건강 주의 포인트 한 줄 (오행 결핍/과다와 연결지어)
- 전체를 관통하는 한 문장 요약 (이 사람을 한 문장으로 표현)

출력은 반드시 위 7개 항목만, 다른 설명 없이 나열하라.
""".strip()


# ---------------------------------------------------------------------------
# 섹션 정의 (레고 블록)
# ---------------------------------------------------------------------------

def _req_총론(data, period=None):
    return f"""
[요청]
이 사주 전체를 한눈에 보여주는 '총론' 섹션을 작성하라 (800~1000자 분량).
- 오행 분포가 어느 쪽으로 치우쳐 있는지, 그것이 성향에 어떤 색깔을 주는지
- 일간({data['day_master']})을 중심으로 이 사람이 가진 전반적 기질의 큰 그림
- 이 사주의 가장 눈에 띄는 특징 한두 가지를 첫 문단에서 짚어줄 것
"""

def _req_성격(data, period=None):
    return f"""
[요청]
'성격과 기질' 섹션을 작성하라 (1000~1200자 분량).
- 일간({data['day_master']}) 오행의 기본 속성을 성격으로 풀어낼 것
- 강점 3가지, 보완하면 좋을 점 2가지를 구체적 상황 예시와 함께 제시
- 대인관계에서 이 사람이 보이는 전형적인 패턴
"""

def _req_대운흐름(data, period=None):
    steps_text = chr(10).join(f"  {s['age_start']}~{s['age_end']}세: {s['ganzhi']}" for s in data['daeun']['steps'][:6])
    return f"""
[대운 데이터]
방향: {data['daeun']['direction']}, 첫 대운 시작 나이: {data['daeun']['daeun_start_age']}세
{steps_text}

[요청]
'대운 흐름' 섹션을 작성하라 (1200~1500자 분량).
- 각 대운 구간이 원국(原局)과 만나 어떤 색깔의 시기가 되는지 순서대로 설명
- 특히 상승/도약이 기대되는 구간과, 신중해야 할 구간을 구분해서 짚어줄 것
- 현재 나이대에 해당하는 대운을 강조해서 조금 더 자세히 다룰 것
"""

def _req_재물운(data, period=None):
    return """
[요청]
'재물운' 섹션을 작성하라 (600~800자 분량).
- 이 사주의 재물을 대하는 성향(안정형/도전형 등)
- 돈이 들어오고 나가는 패턴의 경향
- 구체적 종목/투자처 추천은 금지. "이런 방식의 관리가 이 사주와 잘 맞는다" 수준으로만.
"""

def _req_애정운(data, period=None):
    return """
[요청]
'애정·결혼운' 섹션을 작성하라 (600~800자 분량).
- 연애에서 이 사람이 보이는 전형적 패턴과 선호하는 관계의 색깔
- 궁합이 좋은 상대방의 특성 경향
- 확정적 결혼시기 단언은 피하고 "~시기에 인연의 기운이 강해진다" 정도로 표현
"""

def _req_건강운(data, period=None):
    return """
[요청]
'건강운' 섹션을 작성하라 (400~600자 분량).
- 오행 분포상 상대적으로 약한 오행과 연관지어 평소 관리하면 좋은 생활습관 제안
- 특정 질병명을 단정하지 말 것. "~부위/~기능에 신경쓰면 좋다" 수준으로.
- 반드시 "정확한 진단은 의료 전문가와 상담하라"는 문구로 마무리
"""

def _req_신년세운(data, period):
    se_un = period["se_un"]
    return f"""
[올해 세운(歲運) 데이터]
{period['year']}년 세운: {se_un['str']}({se_un['hanja']}) - 오행 {se_un['gan_oheng']}/{se_un['ji_oheng']}

[요청]
'{period['year']}년 신년운세' 섹션을 작성하라 (1000~1200자 분량).
- 올해 세운({se_un['str']})이 원국(原局)과 만나 어떤 흐름을 만드는지
- 상반기/하반기 정도로 나눠서 흐름의 변화를 짚어줄 것
- 올해 특히 주의하거나 기대할 만한 부분을 재물/애정/건강 각 한 문장씩 짧게 언급
"""

def _req_월간세운(data, period):
    wol_un = period["wol_un"]
    return f"""
[이번 달 월운(月運) 데이터]
{period['year']}년 {period['month']}월 월운: {wol_un['str']}({wol_un['hanja']}) - 오행 {wol_un['gan_oheng']}/{wol_un['ji_oheng']}

[요청]
'이번 달 운세' 섹션을 작성하라 (500~700자 분량).
- 이번 달 월운이 원국과 만나 이번 한 달 어떤 분위기를 만드는지
- 이번 달 안에 하면 좋은 일 / 피하면 좋은 일을 구체적으로 1~2개씩 제시
"""

def _req_사업운(data, period=None):
    return """
[요청]
'사업·창업운' 섹션을 작성하라 (700~900자 분량).
- 이 사주가 사업/창업에 유리한 기질인지, 어떤 방식(단독형/동업형 등)이 잘 맞는지
- 대운 흐름상 사업을 벌이기에 유리한 시기 경향
- 무리한 확장을 조심해야 할 신호가 있다면 함께 언급 (구체적 투자 추천은 금지)
"""

def _req_이직운(data, period=None):
    return """
[요청]
'이직·취업운' 섹션을 작성하라 (700~900자 분량).
- 이 사주가 잘 맞는 직업적 환경(조직형/자유형, 안정형/변화형 등)
- 이직·이동을 고려하기에 유리한 시기 경향 (대운 흐름 참고)
- 커리어에서 이 사람의 강점을 살릴 수 있는 포지션 방향 제시
"""

def _req_학업운(data, period=None):
    return """
[요청]
'학업운' 섹션을 작성하라 (600~800자 분량).
- 이 사주에 잘 맞는 학습 스타일(집중형/분산형, 이론형/실전형 등)
- 학업에 유리한 시기 경향
- 집중력이 흐트러지기 쉬운 시기나 상황이 있다면 관리법과 함께 언급
"""

def _req_자녀운(data, period=None):
    return """
[요청]
'자녀운' 섹션을 작성하라 (600~800자 분량).
- 이 사주가 자녀와의 관계에서 보이는 전형적 성향 (엄격함/친구같음 등)
- 자녀를 대할 때 강점이 될 수 있는 부분과, 유의하면 좋을 부분
- 확정적 자녀 유무/시기 단언은 하지 말 것, 성향과 태도 위주로 서술
"""

def _req_십신해설(data, period=None):
    sipsin = data["sipsin"]
    lines = "\n".join(
        f"  {v['label']}({data[k]['gan']}): {v['sipsin']} - {v['meaning']}"
        for k, v in sipsin.items()
    )
    return f"""
[십신(十神) 데이터 — 일간 {data['day_master']} 기준]
{lines}

[요청]
'십신으로 보는 나와 주변' 섹션을 작성하라 (1200~1500자 분량).
- 위 십신 데이터를 근거로, 이 사람이 가족·동료·주변 사람들과 맺는 관계의 패턴을 설명
- 각 십신이 나타내는 의미를 그대로 나열하지 말고, 이 사주 전체 맥락에서 자연스럽게 녹여 서술
- 십신이라는 용어를 처음 듣는 사람도 이해할 수 있도록 쉬운 말로 풀어줄 것
- 마지막에 이 사람이 대인관계에서 강점으로 삼을 수 있는 부분을 한 문단으로 정리
"""

def _req_오행상세(data, period=None):
    dist = data["oheng_distribution"]
    strongest = max(dist, key=dist.get)
    weakest = min(dist, key=dist.get)
    return f"""
[오행 분포 데이터]
{dist}
가장 강한 오행: {strongest} / 가장 약한 오행: {weakest}

[요청]
'오행으로 보는 기질의 결' 섹션을 작성하라 (1400~1700자 분량). 목·화·토·금·수 다섯 오행을
각각 소제목으로 나누고, 이 사주에 각 오행이 몇 개씩 있는지 데이터를 근거로 짧게(오행당
200~300자) 설명하라.
- 많이 가진 오행: 그 기운이 강하게 드러나는 성향을 구체적으로
- 적거나 없는 오행: 부족해서 나타날 수 있는 경향과, 일상에서 보완하는 방법을 함께
- 오행 다섯 개를 전부 다루되, 이 사주에서 가장 두드러지는 오행({strongest})에 대한
  설명을 가장 비중있게 다룰 것
"""

def _req_5개년세운(data, period_list):
    lines = "\n".join(
        f"  {p['year']}년: {p['se_un']['str']}({p['se_un']['hanja']}) - 오행 {p['se_un']['gan_oheng']}/{p['se_un']['ji_oheng']}"
        for p in period_list
    )
    return f"""
[향후 5개년 세운 데이터]
{lines}

[요청]
'향후 5년 흐름'  섹션을 작성하라 (1800~2200자 분량). 위 5개 연도를 각각 소제목으로 나누고,
연도별로 250~350자씩 서술하라.
- 각 연도의 세운이 원국(原局)과 만나 어떤 색깔의 해가 되는지
- 5년 전체를 관통하는 흐름(상승기/다지는 시기/전환점 등)이 있다면 마지막에 한 문단으로 정리
- 연도마다 서로 다른 톤이 드러나야 한다 (모든 해가 비슷하게 읽히면 안 됨)
"""


SECTION_SPECS = {
    "총론":     {"title": "총론",           "eyebrow": "OVERVIEW",        "subtitle": "이 사주의 큰 그림",         "requirement_fn": _req_총론,     "needs_period": False},
    "성격":     {"title": "성격과 기질",     "eyebrow": "TEMPERAMENT",     "subtitle": "타고난 그릇의 모양",        "requirement_fn": _req_성격,     "needs_period": False},
    "대운흐름": {"title": "대운의 흐름",     "eyebrow": "TEN-YEAR CYCLES", "subtitle": "10년 주기로 바뀌는 흐름",   "requirement_fn": _req_대운흐름, "needs_period": False},
    "재물운":   {"title": "재물운",         "eyebrow": "WEALTH",          "subtitle": "돈을 대하는 태도와 흐름",   "requirement_fn": _req_재물운,   "needs_period": False},
    "애정운":   {"title": "애정·결혼운",    "eyebrow": "LOVE & MARRIAGE", "subtitle": "사람과 사람이 만나는 방식", "requirement_fn": _req_애정운,   "needs_period": False},
    "건강운":   {"title": "건강운",         "eyebrow": "WELLBEING",       "subtitle": "몸의 균형을 살피는 법",     "requirement_fn": _req_건강운,   "needs_period": False},
    "신년세운": {"title": "신년운세",       "eyebrow": "THIS YEAR",       "subtitle": "올해, 어떤 흐름이 올까",    "requirement_fn": _req_신년세운, "needs_period": True},
    "월간세운": {"title": "이번 달 운세",   "eyebrow": "THIS MONTH",      "subtitle": "이번 달의 흐름",           "requirement_fn": _req_월간세운, "needs_period": True},
    "사업운":   {"title": "사업·창업운",    "eyebrow": "BUSINESS",        "subtitle": "일을 벌이기 좋은 때",       "requirement_fn": _req_사업운,   "needs_period": False},
    "이직운":   {"title": "이직·취업운",    "eyebrow": "CAREER",          "subtitle": "커리어의 방향과 시기",      "requirement_fn": _req_이직운,   "needs_period": False},
    "학업운":   {"title": "학업운",         "eyebrow": "STUDY",           "subtitle": "집중이 잘 되는 시기",       "requirement_fn": _req_학업운,   "needs_period": False},
    "자녀운":   {"title": "자녀운",         "eyebrow": "FAMILY",          "subtitle": "자녀와 관계 맺는 방식",     "requirement_fn": _req_자녀운,   "needs_period": False},
    "십신해설": {"title": "십신으로 보는 나와 주변", "eyebrow": "TEN GODS", "subtitle": "관계 속에서 드러나는 기질", "requirement_fn": _req_십신해설, "needs_period": False},
    "오행상세": {"title": "오행으로 보는 기질의 결", "eyebrow": "FIVE ELEMENTS", "subtitle": "목화토금수, 다섯 결의 균형", "requirement_fn": _req_오행상세, "needs_period": False},
    "5개년세운": {"title": "향후 5년 흐름", "eyebrow": "5-YEAR OUTLOOK", "subtitle": "다가올 다섯 해의 색깔",      "requirement_fn": _req_5개년세운, "needs_period": False, "needs_period_list": True},
}


def build_section_prompt(section, data, profile_kernel=None, prior_sections_summary=None,
                          period=None, period_list=None, extra_context=""):
    if section not in SECTION_SPECS:
        raise ValueError(f"알 수 없는 섹션: {section}")
    spec = SECTION_SPECS[section]

    pillars_text = _format_pillars(data)

    consistency_block = ""
    if profile_kernel:
        consistency_block += f"""
[일관성 기준 — 반드시 지킬 것]
아래는 이 사주에 대해 이미 확정된 핵심 설정이다. 지금 작성하는 섹션은 반드시 이
설정과 같은 인물을 묘사하는 것처럼 자연스럽게 이어져야 한다. 여기 나온 기질/강점/
성향과 모순되는 내용을 쓰지 마라. 표현은 섹션마다 다양하게 바꿔도 되지만, 핵심
성격 판단 자체는 절대 바꾸지 마라.

{profile_kernel}
"""
    if prior_sections_summary:
        consistency_block += f"""
[이미 작성된 이전 섹션들에서 언급된 내용]
아래 내용과 사실관계가 부딪히지 않게 하라 (같은 이야기를 반복할 필요는 없다,
모순만 피하면 된다).

{prior_sections_summary}
"""

    base_header = f"""
아래는 한 사람의 정확하게 계산된 사주팔자 데이터다. 이 데이터는 이미 검증된 계산
엔진으로 산출된 것이므로 다시 계산하거나 의심하지 말고, 이 값을 있는 그대로 근거로
삼아 해석문만 작성하라.

[사주 원국 데이터]
{pillars_text}
{consistency_block}
{COMMON_STYLE_GUIDE}
"""

    if spec["needs_period"] and period is None:
        raise ValueError(f"섹션 '{section}'은(는) period(세운/월운 데이터)가 필요합니다.")
    if spec.get("needs_period_list") and period_list is None:
        raise ValueError(f"섹션 '{section}'은(는) period_list(여러 해의 세운 데이터)가 필요합니다.")

    if spec.get("needs_period_list"):
        requirement = spec["requirement_fn"](data, period_list)
    else:
        requirement = spec["requirement_fn"](data, period)
    return base_header + requirement + ("\n\n" + extra_context if extra_context else "")


# ---------------------------------------------------------------------------
# 상품 카탈로그 — 여기에 항목을 추가/수정하면 랜딩페이지·서버가 그대로 따라간다.
# ---------------------------------------------------------------------------

PRODUCTS = [
    {"id": "full", "name": "종합 사주 리포트", "price": 19900,
     "description": "총론부터 대운·재물·애정·건강까지 한번에",
     "sections": ["총론", "성격", "대운흐름", "재물운", "애정운", "건강운"]},
    {"id": "premium", "name": "프리미엄 심층 리포트", "price": 39900,
     "description": "십신·오행 심층분석 + 향후 5년 흐름까지 총망라",
     "sections": ["총론", "성격", "오행상세", "십신해설", "대운흐름", "5개년세운",
                  "재물운", "사업운", "애정운", "이직운", "학업운", "자녀운", "건강운"]},
    {"id": "new_year", "name": "신년운세", "price": 9900,
     "description": "올해 한 해의 흐름을 짚어드립니다",
     "sections": ["총론", "신년세운", "재물운", "애정운", "건강운"]},
    {"id": "love", "name": "연애운세", "price": 7900,
     "description": "연애 스타일과 애정운 심층 분석",
     "sections": ["성격", "애정운"]},
    {"id": "wealth", "name": "재물운", "price": 6900,
     "description": "돈을 대하는 태도와 재물의 흐름",
     "sections": ["총론", "재물운"]},
    {"id": "business", "name": "사업·창업운", "price": 8900,
     "description": "사업을 벌이기 좋은 시기와 방향",
     "sections": ["총론", "대운흐름", "사업운"]},
    {"id": "career", "name": "이직·취업운", "price": 7900,
     "description": "커리어 방향과 이직 타이밍",
     "sections": ["성격", "이직운"]},
    {"id": "monthly", "name": "월간운세", "price": 4900,
     "description": "이번 달의 흐름만 짧고 굵게",
     "sections": ["월간세운"]},
    {"id": "health", "name": "건강운", "price": 5900,
     "description": "몸의 균형을 살피는 법",
     "sections": ["총론", "건강운"]},
    {"id": "study", "name": "학업운", "price": 6900,
     "description": "학습 스타일과 집중이 잘 되는 시기",
     "sections": ["성격", "학업운"]},
    {"id": "children", "name": "자녀운", "price": 6900,
     "description": "자녀와 관계 맺는 방식",
     "sections": ["총론", "자녀운"]},
]

PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}


if __name__ == "__main__":
    from saju_core import calculate_saju, calculate_period_pillars
    data = calculate_saju(1990, 5, 15, 10, 30, gender="M")
    period = calculate_period_pillars()
    for p in PRODUCTS:
        print(f"{p['id']:12s} {p['name']:12s} {p['price']:>7,}원  섹션: {p['sections']}")
    print()
    print(build_section_prompt("신년세운", data, period=period))
