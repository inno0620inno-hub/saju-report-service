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
이 사주 전체를 한눈에 보여주는 '총론' 섹션을 작성하라 (1400~1600자 분량).
- 오행 분포가 어느 쪽으로 치우쳐 있는지, 그것이 성향에 어떤 색깔을 주는지
- 일간({data['day_master']})을 중심으로 이 사람이 가진 전반적 기질의 큰 그림
- 이 사주의 가장 눈에 띄는 특징 한두 가지를 첫 문단에서 짚어줄 것
"""

def _req_성격(data, period=None):
    return f"""
[요청]
'성격과 기질' 섹션을 작성하라 (3000~3200자 분량).
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
'대운 흐름' 섹션을 작성하라 (3000~3200자 분량).
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
'사업·창업운' 섹션을 작성하라 (2800~3000자 분량).
- 이 사주가 사업/창업에 유리한 기질인지, 어떤 방식(단독형/동업형 등)이 잘 맞는지
- 대운 흐름상 사업을 벌이기에 유리한 시기 경향
- 무리한 확장을 조심해야 할 신호가 있다면 함께 언급 (구체적 투자 추천은 금지)
"""

def _req_이직운(data, period=None):
    return """
[요청]
'이직·취업운' 섹션을 작성하라 (2800~3000자 분량).
- 이 사주가 잘 맞는 직업적 환경(조직형/자유형, 안정형/변화형 등)
- 이직·이동을 고려하기에 유리한 시기 경향 (대운 흐름 참고)
- 커리어에서 이 사람의 강점을 살릴 수 있는 포지션 방향 제시
"""

def _req_학업운(data, period=None):
    return """
[요청]
'학업운' 섹션을 작성하라 (1400~1600자 분량).
- 이 사주에 잘 맞는 학습 스타일(집중형/분산형, 이론형/실전형 등)
- 학업에 유리한 시기 경향
- 집중력이 흐트러지기 쉬운 시기나 상황이 있다면 관리법과 함께 언급
"""

def _req_자녀운(data, period=None):
    return """
[요청]
'자녀운' 섹션을 작성하라 (1400~1600자 분량).
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
'십신으로 보는 나와 주변' 섹션을 작성하라 (3000~3200자 분량).
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

_OHENG_DETAIL_INFO = {
    "목": {"symbol": "성장과 확장", "body_part": "간·눈"},
    "화": {"symbol": "열정과 표현", "body_part": "심장·혈액순환"},
    "토": {"symbol": "안정과 신뢰", "body_part": "비장·소화기"},
    "금": {"symbol": "결단과 정리", "body_part": "폐·호흡기"},
    "수": {"symbol": "지혜와 유연함", "body_part": "신장·수분대사"},
}

def _req_오행개별(data, period=None, oheng_name=None):
    dist = data["oheng_distribution"]
    count = dist[oheng_name]
    info = _OHENG_DETAIL_INFO[oheng_name]
    level = "많은 편" if count >= 3 else ("적당한 편" if count == 2 else ("적은 편" if count == 1 else "거의 없는 편"))
    return f"""
[이 사주의 {oheng_name}(五行) 데이터]
개수: {count}개 ({level}) / 상징: {info['symbol']} / 관련 신체부위: {info['body_part']}

[요청]
오행 중 '{oheng_name}' 하나에만 집중하는 섹션을 작성하라 (500~650자 분량).
- 이 사주에 {oheng_name} 기운이 {level}이라는 데이터를 근거로 시작할 것
- {oheng_name}이(가) 상징하는 '{info['symbol']}'의 기운이 이 사람에게 어떻게 나타나는지
  (많으면 강점으로, 적으면 보완이 필요한 지점으로)
- 일상에서 이 오행의 기운을 다루는 실용적인 팁 하나로 마무리
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


def _req_대운현재(data, period=None):
    steps = data["daeun"]["steps"]
    # 현재 나이대에 해당하는 대운 구간 추정 (오늘 연도 기준, 정확한 나이는 몰라도 첫 구간을 예시로 사용)
    current = steps[1] if len(steps) > 1 else steps[0]
    return f"""
[집중 분석 대상 대운 구간]
{current['age_start']}~{current['age_end']}세: {current['ganzhi']}

[요청]
'지금 이 대운, 자세히 들여다보기' 섹션을 작성하라 (3000~3200자 분량).
- 이 구간이 원국과 만나 구체적으로 어떤 국면을 만드는지
- 이 시기에 특히 신경 쓰면 좋을 선택과, 놓치면 아까운 기회를 함께
- 앞서 '대운의 흐름'에서 이미 다룬 내용을 반복하지 말고, 이 구간 하나만 깊게 파고들 것
"""

def _req_대운다음(data, period=None):
    steps = data["daeun"]["steps"]
    nxt = steps[2] if len(steps) > 2 else steps[-1]
    return f"""
[미리보기 대상 대운 구간]
{nxt['age_start']}~{nxt['age_end']}세: {nxt['ganzhi']}

[요청]
'다음 대운 미리보기 — 지금부터 준비할 것' 섹션을 작성하라 (2800~3000자 분량).
- 다가올 이 구간이 어떤 색깔로 바뀌는지, 지금 구간과 무엇이 달라지는지
- 지금부터 미리 준비해두면 좋을 것을 구체적으로 2~3가지 제안
"""

def _req_재물심층(data, period=None):
    steps_text = chr(10).join(f"  {s['age_start']}~{s['age_end']}세: {s['ganzhi']}" for s in data['daeun']['steps'][:5])
    return f"""
[대운 데이터]
{steps_text}

[요청]
'연령대별 재물의 흐름' 섹션을 작성하라 (3000~3200자 분량). 위 대운 구간을 2~3개씩 묶어서
인생의 시기(예: 기반을 다지는 시기 / 확장하는 시기 / 수확하는 시기)로 나누고, 각 시기마다
재물이 들어오고 쌓이는 패턴이 어떻게 달라지는지 서술하라.
- 앞의 '재물운' 섹션과 내용이 겹치지 않게, 이번엔 '시간 흐름'에 초점을 맞출 것
- 시기마다 소제목을 붙여서 읽기 쉽게 구성
"""

def _req_애정심층(data, period=None):
    steps_text = chr(10).join(f"  {s['age_start']}~{s['age_end']}세: {s['ganzhi']}" for s in data['daeun']['steps'][:5])
    return f"""
[대운 데이터]
{steps_text}

[요청]
'연령대별 인연의 흐름' 섹션을 작성하라 (3000~3200자 분량). 대운 구간을 시기별로 묶어서
인연과 관계의 결이 어떻게 달라지는지 서술하라.
- 앞의 '애정운' 섹션과 내용이 겹치지 않게, 이번엔 '시간 흐름'에 초점을 맞출 것
- 확정적 결혼시기 단언은 피하고 "인연의 기운이 강해지는 시기" 식으로 표현
- 시기마다 소제목을 붙여서 읽기 쉽게 구성
"""

def _req_인간관계심층(data, period=None):
    sipsin = data["sipsin"]
    lines = "\n".join(f"  {v['label']}: {v['sipsin']}" for k, v in sipsin.items())
    return f"""
[십신 데이터]
{lines}

[요청]
'관계 속의 나 — 더 깊이' 섹션을 작성하라 (3000~3200자 분량). 앞서 '십신으로 보는 나와 주변'
섹션에서 전체적인 개요를 다뤘다면, 이번엔 아래 세 가지 구체적인 관계로 나눠서 각각
250~350자씩 서술하라.
- 가족(부모·형제)과의 관계에서 나타나는 패턴
- 직장·조직 내 동료·상사와의 관계 패턴
- 친밀한 관계(연인·배우자)에서 나타나는 패턴
"""

_RELATIONSHIP_TOPICS = {
    "가족": "부모·형제와의 관계에서 나타나는 패턴 — 어릴 때부터 이어지는 가족 안에서의 역할",
    "직장": "직장·조직 내 동료·상사와의 관계 패턴 — 협업 스타일, 갈등을 다루는 방식",
    "연인": "친밀한 관계(연인·배우자)에서 나타나는 패턴 — 가까운 사이일수록 드러나는 모습",
}

def _req_관계개별(data, period=None, relation_type=None):
    sipsin = data["sipsin"]
    lines = "\n".join(f"  {v['label']}: {v['sipsin']}" for k, v in sipsin.items())
    topic = _RELATIONSHIP_TOPICS[relation_type]
    return f"""
[십신 데이터]
{lines}

[요청]
'{relation_type} 관계에서의 나' 섹션을 작성하라 (700~850자 분량).
- 주제: {topic}
- 위 십신 데이터를 근거로 이 사람이 {relation_type} 관계에서 보이는 구체적인 패턴을 서술
- 이 관계를 더 편안하게 만들기 위한 실용적인 조언 한두 가지로 마무리
"""

def _req_건강심층(data, period=None):
    dist = data["oheng_distribution"]
    weakest = min(dist, key=dist.get)
    return f"""
[오행 분포 데이터]
{dist}
가장 약한 오행: {weakest}

[요청]
'오행 균형을 위한 생활 루틴' 섹션을 작성하라 (2800~3000자 분량). 앞의 '건강운' 섹션이
전반적 경향을 다뤘다면, 이번엔 실천 가능한 구체적 루틴 위주로 작성하라.
- 부족한 오행({weakest})을 보완하는 데 도움이 되는 생활 습관을 계절/시간대/음식/활동
  카테고리로 나눠서 각각 구체적으로 제안
- "~카테고리별로 소제목을 붙여서 체크리스트처럼 읽히게 구성
"""

def _req_총평(data, period=None):
    return f"""
[요청]
'총평 — 이 사주를 한 문장으로' 섹션을 작성하라 (2000~2200자 분량). 리포트 전체를 마무리하는
페이지다.
- 지금까지 다룬 내용을 관통하는 이 사람의 핵심 정체성을 다시 한 문장으로 정리
- 이 리포트에서 나온 조언 중 '가장 먼저 실천하면 좋을 것' 3가지를 실천 가능한 행동으로 정리
- 마지막 문단은 따뜻하게 격려하는 톤으로 마무리
"""

def _req_신살(data, period=None):
    gwiin = data["cheoneulgwiin"]
    if gwiin["has_gwiin"]:
        found_text = ", ".join(f"{f['pillar']}({f['jiji']})" for f in gwiin["found"])
        gwiin_desc = f"이 사주에는 천을귀인이 있다 ({found_text}에 해당)."
    else:
        gwiin_desc = "이 사주에는 천을귀인이 뚜렷하게 나타나지 않는다."
    return f"""
[천을귀인(天乙貴人) 데이터]
{gwiin_desc}

[요청]
'신살(神殺)로 보는 특별한 기운' 섹션을 작성하라 (800~1000자 분량).
- 먼저 '천을귀인'이 무엇인지 쉬운 말로 짧게 설명 (어려운 사람을 만났을 때 귀인의
  도움을 받기 쉬운 기운이라는 정도로)
- 위 데이터를 근거로, 이 사주에 천을귀인이 있는지 없는지를 명확히 밝히고 의미를 설명
- 있으면: 어떤 상황에서 귀인의 도움이 나타나기 쉬운지
- 없으면: 그렇다고 불리한 것이 아니라, 스스로의 힘으로 길을 만드는 사주라는 식으로
  긍정적으로 풀어줄 것 (신살 없음을 부정적으로 서술하지 말 것)
"""

def _req_궁합가이드(data, period=None):
    day_gan = data["day_master"]
    day_oheng = data["day_pillar"]["gan_oheng"]
    return f"""
[요청]
'좋은 궁합을 알아보는 법' 섹션을 작성하라 (900~1100자 분량). 특정 상대방과의 실제
궁합을 보는 게 아니라, 이 사람({day_gan}, {day_oheng} 일간)이 어떤 유형의 상대와
자연스럽게 잘 맞는 경향이 있는지, 그리고 궁합을 볼 때 무엇을 함께 확인하면 좋은지
안내하는 교육적 성격의 섹션이다.
- 이 사람의 일간 오행과 상생·상극 관계에 있는 오행들이 관계에서 어떤 역할을 하는지
  (상생 관계 상대: 편안함, 상극 관계 상대: 자극과 긴장 등)
- 실제 궁합을 볼 때 일반적으로 함께 고려하는 요소들(두 사람의 오행 균형, 일간 관계 등)을
  간단히 소개
- 특정 개인을 지목한 확정적 궁합 판단은 하지 말고, '두 사람의 사주를 함께 보면 더 정확히
  알 수 있다'는 안내로 마무리
"""

def _req_택일가이드(data, period=None):
    day_oheng = data["day_pillar"]["gan_oheng"]
    weak_oheng = min(data["oheng_distribution"], key=data["oheng_distribution"].get)
    return f"""
[요청]
'좋은 날을 고르는 법' 섹션을 작성하라 (800~1000자 분량). 특정 날짜를 콕 집어 추천하는
게 아니라, 이 사람의 사주 특성을 고려했을 때 '좋은 날을 고를 때 무엇을 우선하면 좋은지'
안내하는 교육적 성격의 섹션이다.
- 전통적으로 택일(擇日)에서 무엇을 확인하는지 간단히 소개 (그 날의 간지가 본인 사주와
  부딪히지 않는지 등)
- 이 사람은 오행 중 {weak_oheng}이(가) 상대적으로 약하니, 중요한 일을 앞두고는 그 기운을
  보완해주는 날/방향/색상 등을 고려하면 좋다는 식으로 실용적으로 연결
- 결혼식, 이사, 개업처럼 사람들이 실제로 택일을 궁금해하는 상황을 1~2개 예로 들 것
- 정확한 날짜는 실제 만세력과 함께 전문가와 상담하는 것을 권장하는 문구로 마무리
"""

def _req_12개월세운(data, months_data):
    lines = "\n".join(
        f"  {m['month']}월: {m['wol_un']['str']}({m['wol_un']['hanja']}) - 오행 {m['wol_un']['gan_oheng']}/{m['wol_un']['ji_oheng']}"
        for m in months_data
    )
    return f"""
[올해 12개월 전체 월운 데이터]
{lines}

[요청]
'달마다 보는 올해 흐름' 섹션을 작성하라 (2200~2600자 분량). 1월부터 12월까지 각 달을
짧은 소제목으로 나누고, 달마다 150~200자씩 서술하라.
- 각 달의 월운이 원국(原局)과 만나 그 달을 어떤 분위기로 만드는지
- 계절 흐름(봄/여름/가을/겨울)에 따라 자연스럽게 톤이 이어지도록
- 특히 흐름이 좋은 달과, 신중해야 할 달을 구분해서 짚어줄 것
"""

_SEASON_MONTHS = {
    "봄": [3, 4, 5], "여름": [6, 7, 8], "가을": [9, 10, 11], "겨울": [12, 1, 2],
}

def _req_계절세운(data, months_data, season_name):
    target_months = _SEASON_MONTHS[season_name]
    season_months_data = [m for m in months_data if m["month"] in target_months]
    lines = "\n".join(
        f"  {m['month']}월: {m['wol_un']['str']}({m['wol_un']['hanja']}) - 오행 {m['wol_un']['gan_oheng']}/{m['wol_un']['ji_oheng']}"
        for m in season_months_data
    )
    return f"""
[{season_name}철(월운 데이터)]
{lines}

[요청]
올해 '{season_name}철 흐름' 섹션을 작성하라 (600~750자 분량). 위 3개월을 각각 소제목으로
나누고, 달마다 180~230자씩 서술하라.
- 각 달의 월운이 원국(原局)과 만나 그 달을 어떤 분위기로 만드는지
- {season_name}철 전체를 관통하는 한 줄 요약을 마지막에 덧붙일 것
"""


# ---------------------------------------------------------------------------
# 용어해설 — AI가 아니라 고정된 정확한 설명을 그대로 사용 (사전적 정의라 매번
# AI에게 새로 쓰게 할 필요가 없고, 고정해두는 편이 오히려 정확하고 비용도 안 든다)
# ---------------------------------------------------------------------------

GLOSSARY_STATIC_TEXT = """사주팔자(四柱八字) — 태어난 연·월·일·시, 네 기둥(四柱)을 각각 천간과 지지 두 글자씩, 총 여덟 글자(八字)로 나타낸 것. 사주 해석의 기본 뼈대가 된다.

일간(日干) — 태어난 날의 천간. 사주 해석에서 '나 자신'을 상징하는 가장 핵심적인 글자로 다룬다.

오행(五行) — 목(木)·화(火)·토(土)·금(金)·수(水) 다섯 가지 기운. 서로 낳아주는 관계(상생)와 서로 억누르는 관계(상극)를 이루며 순환한다.

십신(十神) — 일간을 기준으로 다른 글자들이 어떤 관계인지를 열 가지로 분류한 것 (비견·겁재·식신·상관·편재·정재·편관·정관·편인·정인). 성격, 재물, 관계 등을 해석하는 데 쓰인다.

대운(大運) — 10년 단위로 바뀌는 인생의 큰 흐름. 사주 원국이 '타고난 그릇'이라면, 대운은 그 그릇이 시기마다 어떤 환경 속에 놓이는지를 보여준다.

세운(歲運) — 매년 바뀌는 그 해의 운. 대운이 10년 단위의 큰 흐름이라면, 세운은 1년 단위의 흐름이다.

월운(月運) — 매달 바뀌는 그 달의 운. 세운보다 더 짧은 주기의 흐름을 본다.

음양(陰陽) — 모든 오행은 음과 양으로 다시 나뉜다. 같은 오행이라도 음양에 따라 성질이 달라진다 (예: 같은 목이라도 갑목은 양, 을목은 음).

절기(節氣) — 태양의 위치에 따라 1년을 24개로 나눈 것. 사주에서 연/월이 바뀌는 기준점(예: 입춘)으로 사용되며, 양력 1/1이나 음력 1/1과는 다르다."""


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
    "대운현재": {"title": "지금 이 대운, 자세히", "eyebrow": "CURRENT CYCLE", "subtitle": "지금 서 있는 자리",     "requirement_fn": _req_대운현재, "needs_period": False},
    "대운다음": {"title": "다음 대운 미리보기", "eyebrow": "NEXT CYCLE", "subtitle": "다가올 변화를 위한 준비",   "requirement_fn": _req_대운다음, "needs_period": False},
    "재물심층": {"title": "연령대별 재물의 흐름", "eyebrow": "WEALTH TIMELINE", "subtitle": "시기마다 달라지는 재물의 결", "requirement_fn": _req_재물심층, "needs_period": False},
    "애정심층": {"title": "연령대별 인연의 흐름", "eyebrow": "LOVE TIMELINE", "subtitle": "시기마다 달라지는 인연의 결", "requirement_fn": _req_애정심층, "needs_period": False},
    "인간관계심층": {"title": "관계 속의 나, 더 깊이", "eyebrow": "RELATIONSHIPS", "subtitle": "가족·직장·연인 셋의 결", "requirement_fn": _req_인간관계심층, "needs_period": False},
    "건강심층": {"title": "오행 균형을 위한 생활 루틴", "eyebrow": "DAILY ROUTINE", "subtitle": "실천 가능한 균형의 기술", "requirement_fn": _req_건강심층, "needs_period": False},
    "총평": {"title": "총평 — 이 사주를 한 문장으로", "eyebrow": "CLOSING", "subtitle": "리포트를 닫으며",         "requirement_fn": _req_총평,     "needs_period": False},
    "용어해설": {"title": "용어 해설", "eyebrow": "GLOSSARY", "subtitle": "리포트에 나온 명리학 용어들",         "is_static": True, "static_content": GLOSSARY_STATIC_TEXT},
    "신살":     {"title": "신살로 보는 특별한 기운", "eyebrow": "SPECIAL STARS", "subtitle": "천을귀인, 귀인의 기운", "requirement_fn": _req_신살, "needs_period": False},
    "궁합가이드": {"title": "좋은 궁합을 알아보는 법", "eyebrow": "COMPATIBILITY", "subtitle": "서로 잘 맞는 관계의 결", "requirement_fn": _req_궁합가이드, "needs_period": False},
    "택일가이드": {"title": "좋은 날을 고르는 법", "eyebrow": "DATE SELECTION", "subtitle": "중요한 날, 무엇을 볼까", "requirement_fn": _req_택일가이드, "needs_period": False},
    "12개월세운": {"title": "달마다 보는 올해 흐름", "eyebrow": "MONTH BY MONTH", "subtitle": "1월부터 12월까지",   "requirement_fn": _req_12개월세운, "needs_period": False, "needs_months_data": True},
}

# 오행 5개를 각각 독립된 페이지로 (강제로 페이지 분리 -> 분량 확보 + 가독성)
import functools
for _oh in ["목", "화", "토", "금", "수"]:
    SECTION_SPECS[f"오행_{_oh}"] = {
        "title": f"{_oh}(五行) — {_OHENG_DETAIL_INFO[_oh]['symbol']}",
        "eyebrow": "FIVE ELEMENTS",
        "subtitle": f"이 사주 속 {_oh}의 자리",
        "requirement_fn": functools.partial(_req_오행개별, oheng_name=_oh),
        "needs_period": False,
    }

# 계절 4개를 각각 독립된 페이지로
for _season in ["봄", "여름", "가을", "겨울"]:
    SECTION_SPECS[f"계절_{_season}"] = {
        "title": f"{_season}철 흐름",
        "eyebrow": "SEASONAL FLOW",
        "subtitle": "이 계절, 어떤 기운이 스칠까",
        "requirement_fn": functools.partial(_req_계절세운, season_name=_season),
        "needs_period": False,
        "needs_months_data": True,
    }

# 관계 3종(가족/직장/연인)을 각각 독립된 페이지로
for _rel in ["가족", "직장", "연인"]:
    SECTION_SPECS[f"관계_{_rel}"] = {
        "title": f"{_rel} 관계에서의 나",
        "eyebrow": "RELATIONSHIPS",
        "subtitle": "가까운 사이일수록 드러나는 결",
        "requirement_fn": functools.partial(_req_관계개별, relation_type=_rel),
        "needs_period": False,
    }


def build_section_prompt(section, data, profile_kernel=None, prior_sections_summary=None,
                          period=None, period_list=None, months_data=None, extra_context=""):
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
    if spec.get("needs_months_data") and months_data is None:
        raise ValueError(f"섹션 '{section}'은(는) months_data(12개월 데이터)가 필요합니다.")

    if spec.get("needs_period_list"):
        requirement = spec["requirement_fn"](data, period_list)
    elif spec.get("needs_months_data"):
        requirement = spec["requirement_fn"](data, months_data)
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
     "sections": ["총론", "성격",
                  "오행_목", "오행_화", "오행_토", "오행_금", "오행_수",
                  "십신해설", "신살", "관계_가족", "관계_직장", "관계_연인",
                  "대운흐름", "대운현재", "대운다음", "5개년세운",
                  "계절_봄", "계절_여름", "계절_가을", "계절_겨울",
                  "재물운", "재물심층", "사업운",
                  "애정운", "애정심층", "궁합가이드",
                  "이직운", "학업운", "자녀운", "택일가이드",
                  "건강운", "건강심층",
                  "총평", "용어해설"]},
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
