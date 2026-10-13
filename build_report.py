# -*- coding: utf-8 -*-
"""
build_report.py
saju_core 계산결과 + AI 해석문(섹션 텍스트) + 선택된 섹션 목록을 받아서
template_cover.html / template_body.html에 동적으로 내용을 조립해 최종 PDF
리포트를 생성한다.

---------------------------------------------------------------------------
[2026-09 개편] 예전 버전은 섹션 하나 = 물리 페이지 한 장을 강제로 맞추는
방식(고정 min-height + page-break-after)이었다. 이 방식은:
  - 섹션 내용이 한 페이지보다 살짝만 길어져도 내용이 다음 페이지로
    넘어가면서 원래 페이지 번호가 엉뚱한 빈 페이지에 찍히는 버그가 있었고,
  - 글자 크기를 키우면 무조건 내용을 줄여야만 한 페이지에 맞출 수 있었다.

그래서 지금은 wkhtmltopdf의 실제 페이지 여백(--margin-*) 기능을 쓰고,
섹션은 "새 페이지에서 시작"만 강제하고 그 뒤로는 내용 길이에 맞춰
자연스럽게 여러 페이지로 흘러가게(flow) 바꿨다. 표지는 여백 없이
꽉 채워야 해서 별도 문서(template_cover.html)로 분리해서 따로 렌더링한
뒤 pdfunite로 합친다.

목차(TOC)의 페이지 번호는 실제로 렌더링해보기 전까지는 알 수 없으므로
(섹션이 몇 페이지짜리가 될지 내용 길이에 따라 달라짐), 1차로 숨김
마커를 심어서 렌더링 → 각 마커가 실제로 몇 페이지에 찍혔는지
pdftotext로 확인 → 그 페이지 번호로 목차를 다시 채워서 2차(최종)
렌더링을 하는 2-pass 방식을 쓴다.
---------------------------------------------------------------------------
"""

import subprocess
import os
import re
import json
import math
import random
import datetime
from saju_core import calculate_saju
from report_prompts import SECTION_SPECS

try:                                   # 배경 아트 합성용(순수 파이썬). 없으면 예전 방식으로 자동 폴백
    from pypdf import PdfReader, PdfWriter, Transformation
    _HAVE_PYPDF = True
except Exception:                      # pragma: no cover
    _HAVE_PYPDF = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "report_assets")
ART_DIR = os.path.join(ASSETS_DIR, "art")      # 미리 구워 둔 배경 아트(cover/page/opener .pdf) — report_assets/art_src/build_art.py 로 생성

# wkhtmltopdf(구형 WebKit 엔진)는 CSS 커스텀 프로퍼티(var(--x))를 인식하지
# 못해서 배경색이 그냥 안 먹는 문제가 있었다. 그래서 오행 막대그래프처럼
# 파이썬에서 동적으로 색을 꽂아 넣는 곳은 var() 대신 실제 hex 값을 직접 쓴다.
# (2026-10: 어두운 보랏빛 바탕에서 또렷하도록 이전보다 채도·명도를 올림)
OHENG_COLOR_HEX = {"목": "#3F9E5C", "화": "#D84A36", "토": "#C99A22", "금": "#BDB9AB", "수": "#3C78D0"}
# 오행 바를 그라데이션으로 칠할 때 쓰는, 각 색의 밝은 버전(입체감/윤기를 위함).
OHENG_COLOR_LIGHT = {"목": "#7FE0A0", "화": "#FF8F78", "토": "#F7DA7A", "금": "#F4F1E8", "수": "#80B6FF"}
OHENG_HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}
HANJA_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                   "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                   "二十一", "二十二", "二十三", "二十四", "二十五", "二十六", "二十七", "二十八", "二十九", "三十"]

# 페이지 크기: 9:16 비율(세로형). wkhtmltopdf는 --page-size 프리셋(A4 등) 대신
# --page-width/--page-height로 임의 비율을 지정할 수 있다. 가로 220mm 기준으로
# 잡아야 여백 15mm씩을 빼도 본문 폭이 190mm 정도 남아 사주 원국 카드 4개 등이
# 안 깨진다(가로가 더 좁으면 카드가 글자 크기 대비 너무 좁아져 겹치거나
# 넘칠 수 있음).
PAGE_WIDTH = "220mm"
PAGE_HEIGHT = "391.11mm"  # 220mm * 16/9

# 페이지 본문 여백.
# 중요: wkhtmltopdf의 --margin-left/right는 "빈 공간"이라서 본문 배경색(어두운
# 색)이 거기까지 안 칠해지고 페이지 가장자리에 흰 여백이 남는다. 그런데
# 사용자가 실제로 보는 건 "어두운 화면(박스)" 자체이고, 그 화면의 왼쪽/오른쪽
# 끝에 글자가 딱 붙어 있는 게 문제라고 지적함. 그래서 왼쪽/오른쪽은
# wkhtmltopdf 여백을 0으로 없애서 어두운 배경이 페이지 가장자리까지 꽉
# 채우게(풀블리드) 하고, 대신 그 안에서 CSS padding으로 15mm를 줘서 배경색
# 자체의 가장자리와 글자 사이에 여백이 생기게 한다(template_body.html의
# body { padding-left/right: 15mm } 참고). 위/아래는 기존 방식(페이지 번호
# 자리 확보) 그대로 유지.
BODY_MARGIN_TOP = "28mm"      # 모서리 연꽃 문양(배경 아트)과 첫 줄이 겹치지 않도록 22→28mm
BODY_MARGIN_BOTTOM = "28mm"
BODY_MARGIN_LEFT = "0"
BODY_MARGIN_RIGHT = "0"

WATERMARK_DIV = (
    '<div class="watermark"><div class="watermark-mark">SAMPLE · 미리보기</div></div>'
)


# ---------------------------------------------------------------------------
# 삽화(사이트 캐릭터 금빛도사 이미지 풀) — PDF를 만들 때마다 장(章)별로 무작위로 골라 넣는다.
# report_assets/illustrations/pool.json 의 테마별 목록에서 뽑고, 한 PDF 안에서는 같은 그림을 반복하지 않는다.
# 새 그림을 만들면 illustrations/ 에 1000x640 jpg로 넣고 pool.json에 이름만 추가하면 된다.
# ---------------------------------------------------------------------------
ILLUST_DIR = os.path.join(ASSETS_DIR, "illustrations")
_THEME_RULES = [
    ("wealth", ("재물", "사업", "이직")),
    ("love", ("애정", "연인", "관계", "자녀")),
    ("health", ("건강", "오행", "목", "화", "토", "금", "수")),
    ("time", ("대운", "세운", "계절", "월간", "신년")),
    ("char", ("성격", "십신", "신살")),
    ("work", ("학업", "직장")),
]


def _theme_for(section_key):
    if section_key in ("총론", "pillars"):
        return "overview"
    for theme, keys in _THEME_RULES:
        if any(k in section_key for k in keys):
            return theme
    return "overview"


def _load_illust_pool():
    try:
        with open(os.path.join(ILLUST_DIR, "pool.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_BUBBLES = {
    "overview": ["자, 이 사주의 큰 그림부터 짚어드리지요.", "처음 펼쳐 봐도 눈에 띄는 게 있습니다.", "차분히 따라오시면 다 보입니다."],
    "char": ["겉으로 보이는 모습과 속마음은 조금 다르지요.", "본인도 몰랐던 성향이 여기 있습니다.", "이 부분, 꽤 정확하실 겁니다."],
    "time": ["때가 오면 흐름이 바뀌는 법입니다.", "시기를 알면 서두를 필요가 없지요.", "올라갈 때와 쉬어갈 때가 보입니다."],
    "wealth": ["돈은 흐르는 길이 따로 있습니다.", "들어오는 때와 새는 구멍을 보겠습니다.", "욕심보다 순서가 먼저입니다."],
    "love": ["인연의 결을 한번 읽어보겠습니다.", "마음은 사주에 다 적혀 있지요.", "이 대목은 천천히 읽어보세요."],
    "health": ["몸이 보내는 신호를 짚어드리지요.", "균형을 알면 미리 챙길 수 있습니다.", "무리하지 말라는 얘기입니다."],
    "work": ["갈 길의 방향부터 정해보겠습니다.", "재능이 쓰일 자리가 따로 있습니다.", "오래 갈 일은 사주가 알려줍니다."],
}


def _illustration_html(section_key, used):
    """장 머리에 넣을 삽화 <div>. 풀이 없거나 파일이 없으면 빈 문자열(삽화 없이도 PDF는 정상 생성)."""
    pool = _load_illust_pool()
    theme = _theme_for(section_key)
    names = [n for n in pool.get(theme, []) if os.path.exists(os.path.join(ILLUST_DIR, n + ".jpg"))]
    fresh = [n for n in names if n not in used]
    if not fresh:  # 테마 그림을 다 썼으면 전체 풀에서 안 쓴 것, 그것도 없으면 아무거나
        every = {n for lst in pool.values() for n in lst if os.path.exists(os.path.join(ILLUST_DIR, n + ".jpg"))}
        fresh = [n for n in every if n not in used] or list(every)
    if not fresh:
        return ""
    pick = random.choice(fresh)
    used.add(pick)
    line = random.choice(_BUBBLES.get(theme, _BUBBLES["overview"]))
    return (f'<div class="illust"><img src="illustrations/{pick}.jpg">'
            f'<div class="bubble">{_keep_words(line)}</div></div>')


def render_pillar_cards(data):
    cards = []
    for label, key in [("년주 年柱", "year_pillar"), ("월주 月柱", "month_pillar"),
                        ("일주 日柱", "day_pillar"), ("시주 時柱", "hour_pillar")]:
        p = data[key]
        cards.append(f"""
        <div class="myeongsik-cell"><div class="pillar-card">
          <div class="pillar-label">{label}</div>
          <div class="pillar-char oheng-{p['gan_oheng']}">{p['gan']}</div>
          <div class="pillar-char oheng-{p['ji_oheng']}">{p['ji']}</div>
          <div class="pillar-hanja">{p['hanja']}</div>
        </div></div>""")
    return "\n".join(cards)


def render_oheng_bars(data):
    dist = data["oheng_distribution"]
    total = sum(dist.values()) or 1
    max_count = max(dist.values()) if max(dist.values()) > 0 else 1
    rows = []
    for name in ["목", "화", "토", "금", "수"]:
        count = dist[name]
        bar_pct = int(count / max_count * 100) if max_count else 0
        share_pct = round(count / total * 100)
        color_hex = OHENG_COLOR_HEX[name]
        light_hex = OHENG_COLOR_LIGHT[name]
        hanja = OHENG_HANJA[name]
        # 주의: 이 렌더링 엔진(wkhtmltopdf 0.12.6 patched qt)은 표준 linear-gradient()는
        # 지원하지 않지만(background 선언이 통째로 사라짐) 접두사 문법
        # -webkit-gradient(...) 는 지원한다(2026-10 실측). 단색을 먼저 깔아 두고
        # 그 뒤에 접두사 그라데이션을 덧써서, 어느 쪽이든 막대가 보이게 한다.
        rows.append(f"""
        <div class="oheng-row">
          <div class="oheng-name">
            <span class="oheng-badge" style="border-color:{light_hex}; color:{light_hex};">{hanja}</span>
            <span class="oheng-name-kr">{name}</span>
          </div>
          <div class="oheng-track-cell"><div class="oheng-track"><div class="oheng-fill" style="width:{bar_pct}%; background:{color_hex}; background:-webkit-gradient(linear, left top, right top, from({color_hex}), to({light_hex})); box-shadow:0 0 12px 1px {color_hex}99;"></div></div></div>
          <div class="oheng-count">{count}개<span class="oheng-pct">{share_pct}%</span></div>
        </div>""")
    return "\n".join(rows)


def render_oheng_radar(data):
    """오행 분포를 오각형 레이더로 그린 인라인 SVG.
    구형 엔진이 지원하는 도형·그라데이션·텍스트만 쓴다(SVG blur 필터는 쓰지 않음).
    꼭짓점은 상생 순서(목→화→토→금→수)로 위에서 시계 방향."""
    dist = data["oheng_distribution"]
    order = ["목", "화", "토", "금", "수"]
    W, H, cx, cy, R = 640, 600, 320, 300, 190
    top = max(max(dist.values()), 1)

    def pt(i, r):
        a = math.radians(-90 + 72 * i)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def poly(r):
        return " ".join(f"{pt(i, r)[0]:.1f},{pt(i, r)[1]:.1f}" for i in range(5))

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(W * .86)}" height="{int(H * .86)}" viewBox="0 0 {W} {H}">',
         '<defs><radialGradient id="rgv"><stop offset="0" stop-color="#9a7dff" stop-opacity="0.38"/><stop offset="1" stop-color="#9a7dff" stop-opacity="0"/></radialGradient>'
         '<linearGradient id="rgg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3c4"/><stop offset="1" stop-color="#d4aa3a"/></linearGradient></defs>',
         f'<circle cx="{cx}" cy="{cy}" r="{R + 60}" fill="url(#rgv)"/>']
    for k, frac in enumerate((1 / 3, 2 / 3, 1)):          # 눈금 오각형
        s.append(f'<polygon points="{poly(R * frac)}" fill="{"rgba(154,125,255,0.07)" if k == 2 else "none"}" stroke="rgba(212,170,58,{0.55 if k == 2 else 0.3})" stroke-width="{2 if k == 2 else 1}"/>')
    for i in range(5):                                      # 축
        x, y = pt(i, R)
        s.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="rgba(212,170,58,0.28)" stroke-width="1"/>')
    radii = [max(R * dist[n] / top, R * 0.07) for n in order]
    dpts = " ".join(f"{pt(i, r)[0]:.1f},{pt(i, r)[1]:.1f}" for i, r in enumerate(radii))
    s.append(f'<polygon points="{dpts}" fill="rgba(235,195,90,0.30)" stroke="url(#rgg)" stroke-width="4" stroke-linejoin="round"/>')
    for i, n in enumerate(order):
        x, y = pt(i, radii[i])
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{OHENG_COLOR_LIGHT[n]}" stroke="#0B0714" stroke-width="3"/>')
        bx, by = pt(i, R + 52)                              # 바깥 한자 배지 + 개수
        s.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="31" fill="#120C22" stroke="{OHENG_COLOR_LIGHT[n]}" stroke-width="3"/>'
                 f'<text x="{bx:.1f}" y="{by + 12:.1f}" text-anchor="middle" font-size="34" font-weight="bold" font-family="Noto Serif CJK KR, serif" fill="{OHENG_COLOR_LIGHT[n]}">{OHENG_HANJA[n]}</text>'
                 f'<text x="{bx:.1f}" y="{by + 62:.1f}" text-anchor="middle" font-size="24" font-family="Noto Sans CJK KR, sans-serif" fill="#C9C0AC">{dist[n]}개</text>')
    s.append("</svg>")
    return "".join(s)


# 오행 분포 페이지가 막대그래프만으로 끝나면 여백이 휑해 보인다는 피드백에 따라,
# 가장 강한/약한 오행을 짚어주는 해설 문단을 그래프 아래에 덧붙인다.
OHENG_MEANING_STRONG = {
    "목": "성장과 확장의 기운이 두드러집니다. 새로운 일을 벌이고 키워나가는 추진력이 강점으로 작용합니다.",
    "화": "열정과 표현의 기운이 두드러집니다. 에너지와 추진력이 강점이지만, 급하게 몰아붙이지 않도록 완급 조절이 필요합니다.",
    "토": "안정과 신뢰의 기운이 두드러집니다. 묵묵히 중심을 잡는 힘이 강점으로 작용합니다.",
    "금": "결단과 정리의 기운이 두드러집니다. 맺고 끊는 판단력이 강점이지만, 지나치게 날카로워지지 않도록 유연함을 곁들이는 것이 좋습니다.",
    "수": "지혜와 유연함의 기운이 두드러집니다. 상황 판단이 빠르고 적응력이 뛰어난 것이 강점입니다.",
}
OHENG_MEANING_WEAK = {
    "목": "성장과 확장의 기운이 상대적으로 약한 편입니다. 새로운 시도를 미루는 경향이 있을 수 있으니, 작은 것부터 시작해보는 것을 권합니다.",
    "화": "표현과 열정의 기운이 상대적으로 약한 편입니다. 속마음을 잘 드러내지 않는 편일 수 있으니, 의식적으로 표현하는 연습이 도움이 됩니다.",
    "토": "안정과 신뢰의 기운이 상대적으로 약한 편입니다. 마음이 쉽게 흔들릴 수 있으니, 자신만의 루틴을 만들어 중심을 잡는 것이 좋습니다.",
    "금": "결단과 정리의 기운이 상대적으로 약한 편입니다. 맺고 끊는 것이 어려울 수 있으니, 기한을 미리 정해두는 습관을 권합니다.",
    "수": "지혜와 유연함의 기운이 상대적으로 약한 편입니다. 변화에 적응하는 데 시간이 걸릴 수 있으니, 서두르지 않고 천천히 받아들이는 태도가 도움이 됩니다.",
}


def _render_oheng_talk(data):
    dist = data["oheng_distribution"]
    strongest = max(dist, key=dist.get)
    weakest = min(dist, key=dist.get)
    lines = [
        f"오행 중에서는 {strongest}의 기운이 가장 강하게 나타납니다. "
        f"{OHENG_MEANING_STRONG.get(strongest, '')}"
    ]
    if dist[weakest] == 0 or weakest != strongest:
        lines.append(
            f"반대로 {weakest}의 기운은 상대적으로 가장 약하게 나타납니다. "
            f"{OHENG_MEANING_WEAK.get(weakest, '')}"
        )
    lines.append(
        "오행은 어느 한쪽이 강하거나 약하다고 해서 좋고 나쁜 것이 아니라, "
        "타고난 균형의 특징을 보여주는 지표입니다. 강한 기운은 자연스러운 강점으로 "
        "살리고, 약한 기운은 의식적으로 보완해나가는 것이 좋습니다."
    )
    return "\n\n".join(lines)


def render_daeun_steps(data):
    steps = data["daeun"]["steps"][:6]
    out = []
    for s in steps:
        oheng = s["detail"]["gan_oheng"]
        out.append(f"""
        <div class="daeun-step">
          <div class="daeun-age">{s['age_start']}~{s['age_end']}세</div>
          <div class="daeun-gz oheng-{oheng}">{s['ganzhi']}</div>
        </div>""")
    return "\n".join(out)


def _keep_words(text):
    """
    이 렌더링 엔진(wkhtmltopdf, 구형 WebKit)은 CSS `word-break: keep-all`을
    지원하지 않는다(실측 확인됨 — 있어도 없어도 렌더링이 동일함). 그 결과
    한글 어절 중간에서 줄바꿈이 일어나는 문제가 생긴다
    (예: "흘러가는" → "흘" / "러가는", "사주를" → "사주" / "를").
    그래서 공백으로 나뉜 어절마다 white-space:nowrap 스팬으로 감싸서,
    줄바꿈이 어절 사이(공백)에서만 일어나도록 강제한다.
    """
    parts = re.split(r"(\s+)", text)
    out = []
    for p in parts:
        if p == "" or p.isspace():
            out.append(p)
        else:
            out.append(f'<span style="white-space:nowrap">{p}</span>')
    return "".join(out)


# 문장이 끝나는 지점(마침표/물음표/느낌표 뒤 공백) 기준으로 문장을 나눈다.
# "12세부터"처럼 문장 중간의 숫자/조사에는 이 문자들이 붙지 않으므로
# 오탐 없이 잘 나뉜다.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _format_prose(text):
    """
    한 문단(또는 콜아웃처럼 문단이 아닌 짧은 글) 안에서도 문장마다 줄을
    바꿔서(줄바꿈, <br>) 읽기 편하게 만든다. 사용자 피드백: "문장마다
    줄넘겨 그냥. 그게 보기 편하겠다."
    """
    sentences = _split_sentences(text)
    return "<br>".join(_keep_words(s) for s in sentences)


def _strip_markdown(text):
    """AI가 섞어 쓰는 마크다운 기호(### 제목, --- 구분선, **굵게**, - 목록)를 지워 일반 글로 만든다.
    제목 줄(#)은 앞뒤를 문단으로 분리해 한 문단으로 남긴다."""
    out = []
    for line in text.replace("\r", "").split("\n"):
        t = line.strip()
        if re.fullmatch(r"[-*_=\s]{3,}", t):            # --- / *** / ___ 구분선
            out.append("")
            continue
        is_heading = t.startswith("#")
        t = re.sub(r"^#{1,6}\s*", "", t)                   # ### 제목
        t = re.sub(r"^[-*•]\s+", "", t)                    # - 목록
        t = re.sub(r"\*\*|__|`", "", t)                    # **굵게**, `코드`
        t = re.sub(r"(?<!\w)\*(?=\S)|(?<=\S)\*(?!\w)", "", t)  # *기울임*
        if is_heading:
            out.extend(["", t, ""])
        else:
            out.append(t)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def paragraph_list(text):
    text = _strip_markdown(text)
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return [f"<p>{_format_prose(p)}</p>" for p in parts]


def paragraphs_with_mid(text, mid_html):
    """긴 풀이문은 가운데쯤에 삽화를 한 장 더 끼워 넣는다(문단 10개 이상일 때)."""
    items = paragraph_list(text)
    if mid_html and len(items) >= 10:
        items.insert(len(items) // 2, mid_html)
    return "\n".join(items)


def paragraphs(text):
    text = _strip_markdown(text)
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "\n".join(f"<p>{_format_prose(p)}</p>" for p in parts)


CALLOUTS = {
    "재물운": "본 리포트는 특정 투자처나 종목을 추천하지 않으며, 참고용 성향 분석입니다.",
    "건강운": "본 리포트는 의학적 진단이 아닙니다. 정확한 건강 상태는 반드시 의료 전문가와 상담하시기 바랍니다.",
}


def _marker_span(marker_id):
    """
    화면/인쇄물에는 보이지 않지만(투명·1px) 실제 텍스트로는 렌더링되는 숨김 마커.
    이 마커가 최종 PDF에서 몇 페이지에 찍혔는지 pdftotext로 찾아서
    해당 섹션의 실제 시작 페이지 번호를 알아내는 데 쓴다.
    """
    return f'<span class="pagemark">PGMARK_{marker_id}_END</span>'


def _num_class(s):
    """장 번호 글자 수에 따른 크기 클래스(한 글자는 크게, 二十一처럼 길면 작게)."""
    return {1: "num-1", 2: "num-2"}.get(len(s), "num-3")


def _chapter_head_html(num_str, eyebrow, title_html, sub_html="", illust=""):
    """장 머리: 메달(장 번호) · 영문 라벨 · 제목 · 부제 · 구분선 · 삽화.  배경 장식은 페이지 아트가 담당."""
    sub = f'<div class="chapter-title-sub">{sub_html}</div>' if sub_html else ""
    return f"""
  <div class="chapter-head">
    <div class="chapter-medal"><img src="orn/medal.png"><div class="num {_num_class(num_str)}">{num_str}</div></div>
    <div class="chapter-eyebrow">{eyebrow}</div>
    <div class="chapter-title">{title_html}</div>
    {sub}
    <img class="orn-divider" src="orn/divider.png">
    {illust}
  </div>"""


def _render_pillars_block(data, chapter_num_str, marker_id, watermark=False, illust=""):
    """사주 원국 장 = 3쪽. 각 쪽을 70~80%만 채워 해설 길이가 조금 달라져도 1~2줄만 다음 쪽으로 넘어가는 일이 없게 한다.
       ① 장 도입(큰 삽화)  ② 사주 카드 + 일간 해설 + 오행 레이더  ③ 오행 막대 + 해설"""
    wm = WATERMARK_DIV if watermark else ""
    head = _chapter_head_html(chapter_num_str, "THE FOUR PILLARS", "사주 원국",
                              _keep_words("태어난 순간의 하늘과 땅 — 여덟 글자"), illust)
    return f"""
<div class="section-break">
{wm}{_marker_span(marker_id)}
  {head}
</div>
<div class="section-break">
  <div class="myeongsik">
    {render_pillar_cards(data)}
  </div>
  <div class="body-text">
    <p>{_format_prose(f"이 사주의 일간(본인을 상징하는 글자)은 {data['day_master']}입니다. 오행 중 "
    f"{max(data['oheng_distribution'], key=data['oheng_distribution'].get)}의 기운이 상대적으로 "
    "강하게 나타나며, 이는 이후 섹션에서 다루는 성격과 흐름의 바탕이 됩니다.")}</p>
  </div>
  <div class="oheng-block">
    <div class="chapter-head">
      <div class="chapter-eyebrow">FIVE ELEMENTS</div>
      <div class="chapter-title" style="font-size:80px;">오행(五行) 분포</div>
      <img class="orn-divider" src="orn/divider.png">
    </div>
    <div class="oheng-radar">{render_oheng_radar(data)}</div>
  </div>
</div>
<div class="section-break">
  <div class="oheng-panel" style="margin-top:6mm;">
    {render_oheng_bars(data)}
  </div>
  <div class="body-text" style="margin-top:40px;">
    {paragraphs(_render_oheng_talk(data))}
  </div>
</div>"""


def _render_section_block(section_key, data, section_text, chapter_num_str, marker_id, watermark=False, illust="", illust_mid=""):
    spec = SECTION_SPECS[section_key]
    extra_visual = ""
    if section_key == "대운흐름":
        extra_visual = f"""
  <div class="chapter-title-sub" style="margin-top:-6px; text-align:center;">{_keep_words(f"{data['daeun']['direction']} · {data['daeun']['daeun_start_age']}세부터 시작")}</div>
  <div class="daeun-timeline">
    {render_daeun_steps(data)}
  </div>"""
        subtitle = ""  # 위 extra_visual에서 이미 부제 역할을 하므로 중복 방지
    else:
        subtitle = f'<div class="chapter-title-sub">{_keep_words(spec["subtitle"])}</div>'

    callout_html = ""
    if section_key in CALLOUTS:
        callout_html = f'<div class="callout">{_format_prose(CALLOUTS[section_key])}</div>'

    wm = WATERMARK_DIV if watermark else ""
    head = _chapter_head_html(chapter_num_str, spec['eyebrow'], _keep_words(spec['title']),
                              "" if section_key == "대운흐름" else _keep_words(spec["subtitle"]), illust)

    return f"""
<div class="section-break">
{wm}{_marker_span(marker_id)}
  {head}
  {extra_visual}
  <div class="body-text">
    {paragraphs_with_mid(section_text, illust_mid)}
  </div>
  {callout_html}
</div>"""


def _chapter_mark(i):
    """섹션 인덱스(0부터)를 챕터 표기로 변환. 한자 20개를 넘으면 숫자로 대체."""
    return HANJA_NUMERALS[i] if i < len(HANJA_NUMERALS) else str(i + 1)


def _render_toc_block(section_keys, page_map, watermark=False):
    """
    page_map: {marker_id: 실제 페이지번호(int)} 또는 아직 모르면 빈 dict.
    빈 dict로 부르면(1차 렌더링) 페이지 번호 자리에 '—'를 채워서 목차 항목
    자체의 개수/레이아웃은 최종본과 동일하게 유지한다.
    """
    def _p(marker_id):
        n = page_map.get(marker_id)
        return f"{n:03d}" if n is not None else "—"

    items = [("一", "사주 원국 · 오행 분포", _p("pillars"))]
    for i, key in enumerate(section_keys):
        marker_id = f"sec_{i}"
        items.append((_chapter_mark(i + 1), SECTION_SPECS[key]["title"], _p(marker_id)))

    rows = "\n".join(
        f'<div class="toc-item"><span class="toc-mark">{mark}</span>'
        f'<span class="toc-name">{_keep_words(name)}</span><span class="toc-page">{p}</span></div>'
        for mark, name, p in items
    )

    wm = WATERMARK_DIV if watermark else ""
    return f"""
<div>
{wm}  <div class="toc-head">
    <div class="chapter-eyebrow">CONTENTS</div>
    <div class="chapter-title">목차</div>
    <img class="orn-divider" src="orn/divider.png">
  </div>
  {rows}
</div>"""


def _build_body_html(data, sections, section_order, page_map, watermark=False, bg_css=None):
    template_path = os.path.join(ASSETS_DIR, "template_body.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{BG_CSS}}", bg_css if bg_css is not None else _BG_LEGACY)

    used_illust = set()
    parts = [_render_toc_block(section_order, page_map, watermark=watermark)]
    parts.append(_render_pillars_block(data, HANJA_NUMERALS[0], "pillars", watermark=watermark,
                                       illust=_illustration_html("pillars", used_illust)))
    for i, key in enumerate(section_order):
        chapter_num_str = _chapter_mark(i + 1)
        marker_id = f"sec_{i}"
        parts.append(_render_section_block(key, data, sections[key], chapter_num_str, marker_id, watermark=watermark,
                                           illust=_illustration_html(key, used_illust),
                                           illust_mid=_illustration_html("성격" if _theme_for(key) != "char" else key, used_illust)))

    parts.append('<div class="end-orn"><img src="orn/end.png"><div>金 · 命 · 式</div></div>')   # 맺음 장식
    body_html = "\n".join(parts)
    return html.replace("{{BODY_PAGES}}", body_html)


# ---------------------------------------------------------------------------
# [2026-10 개편] 배경 아트 모드
#   글자 층(wkhtmltopdf)은 배경을 칠하지 않아 PDF가 "투명"이다(2026-10 실측: 모서리 알파 0).
#   그래서 미리 구워 둔 배경 아트(별·성운·금 액자·모서리 문양·마법진 — report_assets/art/*.pdf)를
#   pypdf로 페이지 "밑에" 깔아 합친다. 구형 엔진이 못 그리는 효과를 전부 아트로 해결하는 방식.
#   아트 파일/pypdf가 없거나 합성이 실패하면 예전 방식(CSS 검정 줄무늬 배경)으로 자동 폴백한다.
# ---------------------------------------------------------------------------
_BG_LEGACY = "background: #0B0A09 url('bg_stripes.png');"
_BG_ART = "background: transparent;"
COVER_NAME_TOP, COVER_META_TOP = "1256px", "1350px"     # 표지 아트(아치) 안쪽 하단의 이름/출생정보 위치(글자 층 좌표계 px)
FOOTER_NUM_TOP = "87px"                                # 하단 중앙 쪽번호 타원 안의 세로 위치(바닥글 영역 기준, 글자 층 px)


def _art_ready():
    return _HAVE_PYPDF and all(os.path.exists(os.path.join(ART_DIR, f"{n}.pdf")) for n in ("cover", "page", "opener"))


def _run_wkhtmltopdf(args):
    subprocess.run(["wkhtmltopdf", *args], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _pdf_page_count(path):
    if _HAVE_PYPDF:
        return len(PdfReader(path).pages)
    info = subprocess.run(["pdfinfo", path], check=True, capture_output=True, text=True).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return 1


def _pdf_unite(paths, out_pdf):
    """PDF 이어붙이기: poppler의 pdfunite 우선, 없으면 pypdf."""
    try:
        subprocess.run(["pdfunite", *paths, out_pdf], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        if not _HAVE_PYPDF:
            raise
        w = PdfWriter()
        for p in paths:
            w.append(p)
        with open(out_pdf, "wb") as f:
            w.write(f)


def _find_marker_pages(pdf_path, marker_ids):
    """
    pdftotext로 pdf_path의 각 페이지 텍스트를 확인해서, 각 marker_id가
    처음 등장하는 (1부터 시작하는) 로컬 페이지 번호를 찾는다.
    """
    total_pages = _pdf_page_count(pdf_path)

    remaining = set(marker_ids)
    found = {}
    for page in range(1, total_pages + 1):
        if not remaining:
            break
        text = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), pdf_path, "-"],
            check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"   # 인코딩 명시(윈도우 로컬 실행 대비)
        ).stdout or ""
        flat = re.sub(r"\s+", "", text)      # poppler 버전에 따라 작은 글자 사이에 공백이 끼므로 공백을 지우고 비교
        for marker_id in list(remaining):
            if f"PGMARK_{marker_id}_END" in flat:
                found[marker_id] = page
                remaining.discard(marker_id)
    return found


def _fill_template(src_name, dst_path, values):
    """report_assets/<src_name> 의 {{KEY}} 를 채워 dst_path(같은 폴더 → 상대경로 자원이 그대로 풀림)에 쓴다."""
    with open(os.path.join(ASSETS_DIR, src_name), "r", encoding="utf-8") as f:
        html = f.read()
    for k, v in values.items():
        html = html.replace("{{" + k + "}}", v)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(html)


def _compose_with_art(cover_pdf, body_pdf, opener_pages, out_pdf):
    """글자 층(표지 1장 + 본문) 밑에 배경 아트를 깔아 하나의 PDF로 만든다.
    opener_pages: 본문 PDF 안에서 장(章)이 시작하는 로컬 페이지 번호 집합 → 그 페이지는 '장 도입' 아트."""
    arts = {n: PdfReader(os.path.join(ART_DIR, f"{n}.pdf")).pages[0] for n in ("cover", "page", "opener")}
    cover_reader, body_reader = PdfReader(cover_pdf), PdfReader(body_pdf)
    writer = PdfWriter()

    def put(art_name, text_page):
        tw, th = float(text_page.mediabox.width), float(text_page.mediabox.height)
        bg = arts[art_name]
        sx, sy = tw / float(bg.mediabox.width), th / float(bg.mediabox.height)    # 글자 층과 크기를 정확히 맞춘다
        page = writer.add_blank_page(width=tw, height=th)
        page.merge_transformed_page(bg, Transformation().scale(sx, sy))           # 아래: 배경 아트
        page.merge_page(text_page)                                                  # 위: 글자 층

    put("cover", cover_reader.pages[0])
    for i, tp in enumerate(body_reader.pages, start=1):
        put("opener" if i in opener_pages else "page", tp)
    for pg in writer.pages:                 # 합치는 과정에서 풀린 내용 스트림(글로우 벡터 경로 등)을 다시 압축
        try:
            pg.compress_content_streams()
        except Exception:
            pass
    try:
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)   # 같은 아트 그림은 한 번만 저장
    except Exception:
        pass
    with open(out_pdf, "wb") as f:
        writer.write(f)


def _build(data, name, birth_info, sections, section_order, output_pdf, watermark, art):
    mode = "art" if art else "legacy"
    bg_css = _BG_ART if art else _BG_LEGACY

    # output_pdf(주문별로 고유)를 기반으로 중간 파일명도 고유하게 만든다.
    # 고정된 파일명을 쓰면 여러 주문이 동시에 처리될 때 서로의 중간 파일을
    # 덮어써서 엉뚱한 내용의 PDF가 만들어질 수 있다.
    pdf_stem = os.path.splitext(os.path.basename(output_pdf))[0]
    tmp = lambda suffix: os.path.join(ASSETS_DIR, f"_tmp_{pdf_stem}{suffix}")

    cover_html_path = tmp("_cover.html")
    cover_pdf_path = tmp("_cover.pdf")
    body_pass1_html_path = tmp("_body_pass1.html")
    body_pass1_pdf_path = tmp("_body_pass1.pdf")
    body_final_html_path = tmp("_body_final.html")
    body_final_pdf_path = tmp("_body_final.pdf")
    header_path = tmp("_header.html")
    footer_path = tmp("_footer.html")

    try:
        # ---- 0) 머리글·바닥글 (모드별로 배경/쪽번호 위치가 다름) ---------------
        hf_vals = {"BG_CSS": bg_css, "MODE": mode, "NUM_TOP": FOOTER_NUM_TOP}
        _fill_template("header.html", header_path, hf_vals)
        _fill_template("footer.html", footer_path, hf_vals)

        # ---- 1) 표지 렌더링 (여백 0, 별도 문서) ----------------------------
        _fill_template("template_cover.html", cover_html_path, {
            "BG_CSS": bg_css, "MODE": mode,
            "NAME_TOP": COVER_NAME_TOP, "META_TOP": COVER_META_TOP,
            "NAME": _keep_words(name), "BIRTH_INFO": _keep_words(birth_info),
            "ISSUE_DATE": str(datetime.date.today().year),
            "WATERMARK": '<div class="watermark"><div class="watermark-mark">SAMPLE · 미리보기</div></div>' if watermark else "",
        })
        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-width", PAGE_WIDTH, "--page-height", PAGE_HEIGHT,
            "--margin-top", "0", "--margin-bottom", "0",
            "--margin-left", "0", "--margin-right", "0",
            "-q", cover_html_path, cover_pdf_path,
        ])

        # ---- 2) 본문 1차 렌더링 (목차 페이지번호는 아직 모름 → 마커만 심음) ----
        body_pass1_html = _build_body_html(data, sections, section_order, page_map={}, watermark=watermark, bg_css=bg_css)
        with open(body_pass1_html_path, "w", encoding="utf-8") as f:
            f.write(body_pass1_html)

        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-width", PAGE_WIDTH, "--page-height", PAGE_HEIGHT,
            "--margin-top", BODY_MARGIN_TOP, "--margin-bottom", BODY_MARGIN_BOTTOM,
            "--margin-left", BODY_MARGIN_LEFT, "--margin-right", BODY_MARGIN_RIGHT,
            "-q", body_pass1_html_path,
            "--header-html", header_path, "--header-spacing", "0",
            "--footer-html", footer_path, "--footer-spacing", "0",
            body_pass1_pdf_path,
        ])

        # ---- 3) 마커가 실제로 몇 페이지에 찍혔는지 확인 ------------------------
        marker_ids = ["pillars"] + [f"sec_{i}" for i, _ in enumerate(section_order)]
        local_pages = _find_marker_pages(body_pass1_pdf_path, marker_ids)
        # 표지(cover.pdf)가 항상 1페이지를 차지하므로, 실제 최종 문서에서의
        # 페이지 번호는 본문 내 로컬 페이지 번호 + 1 이다.
        page_map = {marker_id: local_page + 1 for marker_id, local_page in local_pages.items()}

        # ---- 4) 본문 최종 렌더링 (목차에 실제 페이지번호 반영) -----------------
        body_final_html = _build_body_html(data, sections, section_order, page_map=page_map, watermark=watermark, bg_css=bg_css)
        with open(body_final_html_path, "w", encoding="utf-8") as f:
            f.write(body_final_html)

        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-width", PAGE_WIDTH, "--page-height", PAGE_HEIGHT,
            "--margin-top", BODY_MARGIN_TOP, "--margin-bottom", BODY_MARGIN_BOTTOM,
            "--margin-left", BODY_MARGIN_LEFT, "--margin-right", BODY_MARGIN_RIGHT,
            "--page-offset", "1",
            "-q", body_final_html_path,
            "--header-html", header_path, "--header-spacing", "0",
            "--footer-html", footer_path, "--footer-spacing", "0",
            body_final_pdf_path,
        ])

        # ---- 5) 합치기: 아트 모드는 배경 아트 위에 글자 층, 기본 모드는 표지+본문 이어붙이기 ----
        if art:
            _compose_with_art(cover_pdf_path, body_final_pdf_path, set(local_pages.values()), output_pdf)
        else:
            _pdf_unite([cover_pdf_path, body_final_pdf_path], output_pdf)

    finally:
        for p in [cover_html_path, cover_pdf_path, body_pass1_html_path, body_pass1_pdf_path,
                  body_final_html_path, body_final_pdf_path, header_path, footer_path]:
            if os.path.exists(p):
                os.remove(p)


def build_report(data, name, birth_info, sections, section_order=None,
                  product_name="사주 명식 리포트", output_pdf="saju_report.pdf",
                  watermark=False):
    """
    sections: {section_key: 해석문_텍스트} 딕셔너리
    section_order: 섹션을 표시할 순서 (list of keys). None이면 sections의 키 순서 사용.
    watermark: True면 모든 페이지에 '샘플 · 미리보기' 워터마크를 찍는다
               (실제 결제된 리포트와 구분하기 위한 테스트/샘플용 표시).
    """
    if section_order is None:
        section_order = list(sections.keys())

    if _art_ready():
        try:
            _build(data, name, birth_info, sections, section_order, output_pdf, watermark, art=True)
            print(f"완성: {output_pdf}")
            return
        except Exception as e:      # 아트 합성이 어떤 이유로든 실패하면, 고객이 PDF를 못 받는 일이 없도록 예전 방식으로 다시 만든다
            print(f"[report] 배경 아트 합성 실패({e!r}) → 기본 모드로 다시 만듭니다")
    _build(data, name, birth_info, sections, section_order, output_pdf, watermark, art=False)
    print(f"완성: {output_pdf}")


if __name__ == "__main__":
    data = calculate_saju(1990, 5, 15, 10, 30, gender="M")
    sections = {
        "총론": "테스트 총론 문단입니다.\n\n두번째 문단.",
        "성격": "테스트 성격 문단입니다.\n\n두번째 문단.",
    }
    build_report(data, "테스트", "1990년생", sections, output_pdf="/tmp/dynamic_test.pdf")
