# -*- coding: utf-8 -*-
"""
build_report.py
saju_core 계산결과 + AI 해석문(섹션 텍스트)을 template.html에 채워서
최종 PDF 리포트를 생성한다.

사용법: python3 build_report.py
"""

import subprocess
import os
from saju_core import calculate_saju

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

OHENG_COLOR_VAR = {"목": "wood", "화": "fire", "토": "earth", "금": "metal", "수": "water"}


def render_pillar_cards(data):
    cards = []
    for label, key in [("년주 年柱", "year_pillar"), ("월주 月柱", "month_pillar"),
                        ("일주 日柱", "day_pillar"), ("시주 時柱", "hour_pillar")]:
        p = data[key]
        cards.append(f"""
        <div class="pillar-card">
          <div class="pillar-label">{label}</div>
          <div class="pillar-char oheng-{p['gan_oheng']}">{p['gan']}</div>
          <div class="pillar-char oheng-{p['ji_oheng']}">{p['ji']}</div>
          <div class="pillar-hanja">{p['hanja']}</div>
        </div>""")
    return "\n".join(cards)


def render_oheng_bars(data):
    dist = data["oheng_distribution"]
    max_count = max(dist.values()) if max(dist.values()) > 0 else 1
    rows = []
    for name in ["목", "화", "토", "금", "수"]:
        count = dist[name]
        pct = int(count / max_count * 100) if max_count else 0
        color_var = OHENG_COLOR_VAR[name]
        rows.append(f"""
        <div class="oheng-row">
          <div class="oheng-name">{name}</div>
          <div class="oheng-track"><div class="oheng-fill" style="width:{pct}%; background:var(--{color_var});"></div></div>
          <div class="oheng-count">{count}</div>
        </div>""")
    return "\n".join(rows)


def render_daeun_steps(data):
    steps = data["daeun"]["steps"][:7]
    out = []
    for s in steps:
        oheng = s["detail"]["gan_oheng"]
        out.append(f"""
        <div class="daeun-step">
          <div class="daeun-age">{s['age_start']}~{s['age_end']}세</div>
          <div class="daeun-gz oheng-{oheng}">{s['ganzhi']}</div>
        </div>""")
    return "\n".join(out)


def paragraphs(text):
    """텍스트를 <p> 태그로 분리."""
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in parts)


def build_report(data, name, birth_info, sections, output_pdf="saju_report.pdf"):
    template_path = os.path.join(SCRIPT_DIR, "report_assets", "template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    pillar_intro = (
        f"이 사주의 일간(본인을 상징하는 글자)은 {data['day_master']}입니다. "
        f"오행 중 {max(data['oheng_distribution'], key=data['oheng_distribution'].get)}"
        f"의 기운이 상대적으로 강하게 나타나며, 이는 이후 섹션에서 다루는 성격과 흐름의 "
        f"바탕이 됩니다."
    )

    replacements = {
        "{{NAME}}": name,
        "{{BIRTH_INFO}}": birth_info,
        "{{ISSUE_DATE}}": "2026",
        "{{PILLAR_CARDS}}": render_pillar_cards(data),
        "{{PILLAR_INTRO}}": pillar_intro,
        "{{OHENG_BARS}}": render_oheng_bars(data),
        "{{SECTION_TOTAL}}": paragraphs(sections["총론"]),
        "{{SECTION_PERSONALITY}}": paragraphs(sections["성격"]),
        "{{DAEUN_DIRECTION}}": data["daeun"]["direction"],
        "{{DAEUN_START_AGE}}": str(data["daeun"]["daeun_start_age"]),
        "{{DAEUN_STEPS}}": render_daeun_steps(data),
        "{{SECTION_DAEUN}}": paragraphs(sections["대운흐름"]),
        "{{SECTION_WEALTH}}": paragraphs(sections["재물운"]),
        "{{SECTION_LOVE}}": paragraphs(sections["애정운"]),
        "{{SECTION_HEALTH}}": paragraphs(sections["건강운"]),
    }

    for k, v in replacements.items():
        html = html.replace(k, v)

    html_path = os.path.join(SCRIPT_DIR, "report_assets", "_rendered.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    subprocess.run(
        ["wkhtmltopdf", "--encoding", "utf-8", "--enable-local-file-access",
         "--page-size", "A4",
         "--margin-top", "0", "--margin-bottom", "0",
         "--margin-left", "0", "--margin-right", "0",
         "-q", html_path, output_pdf],
        check=True
    )
    print(f"완성: {output_pdf}")


if __name__ == "__main__":
    data = calculate_saju(1990, 5, 15, 10, 30, gender="M")

    sections = {
        "총론": """이 사주는 경오년 신사월 기묘일 기사시로, 한여름을 앞둔 뜨거운 계절의 기운이 사주 전체에 짙게 깔려 있습니다. 오행을 보면 화(火)가 세 자리를 차지하며 가장 강하고, 반대로 수(水)는 단 하나도 없어 균형이 한쪽으로 확실히 기울어 있는 사주입니다. 이런 구성은 열정과 추진력이 넘치지만, 그만큼 스스로를 식혀주고 다스려줄 힘이 부족하다는 뜻이기도 합니다.

본인을 상징하는 일간은 기토(己土)입니다. 기토는 큰 산이나 바위 같은 흙이 아니라, 논밭의 부드러운 흙에 가깝습니다. 무언가를 심으면 잘 받아주고 키워내는 성질이죠. 그래서 이 사주의 주인공은 자기주장을 강하게 내세우기보다, 주변 사람이나 상황에 맞춰 유연하게 움직이면서도 결국엔 자기 방식대로 결실을 만들어내는 유형에 가깝습니다.

다만 뜨거운 화 기운이 이 부드러운 흙을 계속 달구고 있는 형국이라, 겉으로는 차분해 보여도 속으로는 열정과 조급함이 함께 끓고 있을 가능성이 큽니다. 물(水)의 기운, 즉 여유와 냉정함을 의식적으로 채워주는 것이 이 사주 전체의 균형을 잡는 핵심 열쇠입니다.""",

        "성격": """기토 일간에 화 기운이 두터운 이 사람은, 첫인상은 온화하고 무난해 보이지만 실제로는 속에 뜨거운 열정을 품고 있는 타입입니다. 겉으로 드러내는 감정과 속마음의 온도차가 있다 보니, 가까워지기 전까지는 "무슨 생각하는지 잘 모르겠다"는 말을 듣는 경우가 많습니다.

강점을 꼽자면 첫째, 포용력입니다. 논밭의 흙처럼 다양한 사람과 의견을 있는 그대로 받아들이는 힘이 있어서, 조직에서 갈등을 조율하는 역할을 자연스럽게 맡게 됩니다. 둘째, 지속력입니다. 화 기운의 추진력과 토 기운의 끈기가 만나, 한번 시작한 일은 웬만해선 끝까지 붙잡고 갑니다. 셋째, 현실감각입니다. 이상보다는 지금 손에 잡히는 결과를 중시하는 실용주의적 태도를 가지고 있습니다.

보완하면 좋을 점은, 우선 감정을 표현하는 데 서투르다는 것입니다. 속에서 열기가 끓어도 겉으로는 참고 삭이는 습관이 있어, 스트레스가 누적되기 쉬운 구조입니다. 의도적으로 감정을 말이나 글로 꺼내는 습관을 들이는 게 도움이 됩니다. 또 하나는 수(水) 기운의 부재에서 오는 조급함입니다. 중요한 결정을 앞두고는 하루 정도 묵혀두고 다시 보는 습관을 들이면, 이 사주가 가진 추진력을 훨씬 안정적으로 쓸 수 있습니다.""",

        "대운흐름": """7세부터 시작되는 첫 대운 신사(辛巳)는 학업과 기초를 다지는 시기로, 원국의 화 기운을 한층 더 뜨겁게 만듭니다. 에너지가 넘치는 만큼 산만해지기 쉬운 시기이니, 한 가지에 집중하는 습관을 들이는 것이 이후를 위한 자산이 됩니다.

17세부터의 임오(壬午) 대운은 이 사주에 처음으로 물(水)의 기운이 스며드는 구간입니다. 그동안 부족했던 냉정함과 균형 감각이 서서히 자리잡으면서, 학업이나 진로에서 중요한 선택을 좀 더 침착하게 내릴 수 있는 힘이 생깁니다.

27세 계미(癸未) 대운부터는 사회생활의 기반이 다져지는 시기로, 꾸준히 쌓아온 실력이 눈에 보이는 성과로 이어지기 시작합니다. 이 시기의 특징은 '천천히, 그러나 확실하게'입니다. 조급하게 큰 것을 노리기보다, 착실한 단계를 밟는 편이 훨씬 유리합니다.

37세 갑신(甲申) 대운은 목(木)과 금(金)이 만나는 구간으로, 새로운 확장과 도전의 기운이 강해지는 시기입니다. 지금까지 다져온 기반 위에서 한 단계 더 도약할 수 있는 타이밍이니, 이 시기가 다가오면 미리 준비해두는 것을 권합니다.""",

        "재물운": """이 사주는 안정보다는 활동성을 통해 재물을 만들어가는 유형에 가깝습니다. 화(火)의 기운이 강한 만큼, 가만히 앉아 있기보다 몸을 움직이고 사람을 만나는 과정에서 기회가 열리는 경향이 있습니다.

다만 수(水)의 부재는 재물을 관리하는 데 있어 계획성이 다소 약할 수 있다는 신호이기도 합니다. 들어올 때는 크게 들어오지만, 나갈 때도 그만큼 쉽게 나갈 수 있는 구조입니다. 고정 지출과 저축을 자동화해두는 식으로 '의지력에 기대지 않는' 관리 장치를 만들어두는 것이 이 사주와 잘 맞는 방식입니다.""",

        "애정운": """겉으로는 무던해 보이지만 속으로는 뜨거운 감정을 품고 있는 타입이라, 연애에서도 처음엔 속도가 느리지만 한번 마음을 열면 깊고 오래가는 관계를 만드는 경향이 있습니다.

이 사주와 잘 맞는 상대는 감정을 있는 그대로 표현해주는 사람입니다. 스스로 표현이 서툰 만큼, 상대가 먼저 다가와주고 마음을 읽어주는 관계에서 훨씬 편안함을 느낍니다. 대운상 수(水) 기운이 들어오는 17세 이후 구간부터 관계에서의 균형 감각이 눈에 띄게 안정되는 흐름을 보입니다.""",

        "건강운": """오행 중 수(水)가 비어있는 구조라, 몸에서는 수 기운이 담당하는 부위 — 신장, 방광, 그리고 전반적인 체내 수분 밸런스 — 에 평소 조금 더 신경을 쓰면 좋습니다. 하루 물 섭취량을 의식적으로 챙기고, 늦은 밤까지 열을 내는 활동(과도한 운동이나 야식 등)은 줄이는 편이 이 사주의 균형에 도움이 됩니다.

화 기운이 강한 사주 특성상 스트레스가 쌓이면 몸에 열로 드러나는 경향(두통, 안구건조, 피부 트러블 등)이 있을 수 있으니, 평소 충분한 휴식과 수분 섭취로 다스려주는 습관을 추천합니다.""",
    }

    build_report(
        data,
        name="홍길동 (샘플)",
        birth_info="1990년 5월 15일 10시 30분생 · 양력 · 남",
        sections=sections,
        output_pdf="saju_report_sample.pdf"
    )
