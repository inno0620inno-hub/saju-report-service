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
from saju_core import calculate_saju
from report_prompts import SECTION_SPECS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "report_assets")

# wkhtmltopdf(구형 WebKit 엔진)는 CSS 커스텀 프로퍼티(var(--x))를 인식하지
# 못해서 배경색이 그냥 안 먹는 문제가 있었다. 그래서 오행 막대그래프처럼
# 파이썬에서 동적으로 색을 꽂아 넣는 곳은 var() 대신 실제 hex 값을 직접 쓴다.
OHENG_COLOR_HEX = {"목": "#4C7A52", "화": "#B03A2E", "토": "#C9A227", "금": "#C9C4B4", "수": "#3A5A8C"}
HANJA_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                   "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                   "二十一", "二十二", "二十三", "二十四", "二十五", "二十六", "二十七", "二十八", "二十九", "三十"]

# 페이지 본문 여백.
# 중요: wkhtmltopdf의 --margin-left/right는 "빈 공간"이라서 본문 배경색(어두운
# 색)이 거기까지 안 칠해지고 페이지 가장자리에 흰 여백이 남는다. 그런데
# 사용자가 실제로 보는 건 "어두운 화면(박스)" 자체이고, 그 화면의 왼쪽/오른쪽
# 끝에 글자가 딱 붙어 있는 게 문제라고 지적함. 그래서 왼쪽/오른쪽은
# wkhtmltopdf 여백을 0으로 없애서 어두운 배경이 페이지 가장자리까지 꽉
# 채우게(풀블리드) 하고, 대신 그 안에서 CSS padding으로 10mm를 줘서 배경색
# 자체의 가장자리와 글자 사이에 여백이 생기게 한다(template_body.html의
# body { padding-left/right: 10mm } 참고). 위/아래는 기존 방식(페이지 번호
# 자리 확보) 그대로 유지.
BODY_MARGIN_TOP = "22mm"
BODY_MARGIN_BOTTOM = "22mm"
BODY_MARGIN_LEFT = "0"
BODY_MARGIN_RIGHT = "0"

WATERMARK_DIV = (
    '<div class="watermark"><div class="watermark-mark">SAMPLE · 미리보기</div></div>'
)


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
    max_count = max(dist.values()) if max(dist.values()) > 0 else 1
    rows = []
    for name in ["목", "화", "토", "금", "수"]:
        count = dist[name]
        pct = int(count / max_count * 100) if max_count else 0
        color_hex = OHENG_COLOR_HEX[name]
        rows.append(f"""
        <div class="oheng-row">
          <div class="oheng-name">{name}</div>
          <div class="oheng-track-cell"><div class="oheng-track"><div class="oheng-fill" style="width:{pct}%; background:{color_hex};"></div></div></div>
          <div class="oheng-count">{count}</div>
        </div>""")
    return "\n".join(rows)


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


def paragraphs(text):
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


def _render_pillars_block(data, chapter_num_str, marker_id, watermark=False):
    wm = WATERMARK_DIV if watermark else ""
    return f"""
<div class="section-break">
{wm}{_marker_span(marker_id)}
  <div class="chapter-head">
    <div class="chapter-mark">{chapter_num_str}</div>
    <div class="chapter-eyebrow">THE FOUR PILLARS</div>
    <div class="chapter-title">사주 원국</div>
    <div class="chapter-title-sub">{_keep_words("태어난 순간의 하늘과 땅 — 여덟 글자")}</div>
    <div class="rule"></div>
  </div>
  <div class="myeongsik">
    {render_pillar_cards(data)}
  </div>
  <div class="body-text">
    <p>{_format_prose(f"이 사주의 일간(본인을 상징하는 글자)은 {data['day_master']}입니다. 오행 중 "
    f"{max(data['oheng_distribution'], key=data['oheng_distribution'].get)}의 기운이 상대적으로 "
    "강하게 나타나며, 이는 이후 섹션에서 다루는 성격과 흐름의 바탕이 됩니다.")}</p>
  </div>
  <div class="chapter-title-sub" style="margin-top:40px; font-size:44px;">오행(五行) 분포</div>
  <div class="oheng-bars">
    {render_oheng_bars(data)}
  </div>
</div>"""


def _render_section_block(section_key, data, section_text, chapter_num_str, marker_id, watermark=False):
    spec = SECTION_SPECS[section_key]
    extra_visual = ""
    if section_key == "대운흐름":
        extra_visual = f"""
  <div class="chapter-title-sub" style="margin-top:-6px;">{_keep_words(f"{data['daeun']['direction']} · {data['daeun']['daeun_start_age']}세부터 시작")}</div>
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

    return f"""
<div class="section-break">
{wm}{_marker_span(marker_id)}
  <div class="chapter-head">
    <div class="chapter-mark">{chapter_num_str}</div>
    <div class="chapter-eyebrow">{spec['eyebrow']}</div>
    <div class="chapter-title">{_keep_words(spec['title'])}</div>
    {subtitle}
    <div class="rule"></div>
  </div>
  {extra_visual}
  <div class="body-text">
    {paragraphs(section_text)}
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
        marker_id = f"sec_{i}_{key}"
        items.append((_chapter_mark(i + 1), SECTION_SPECS[key]["title"], _p(marker_id)))

    rows = "\n".join(
        f'<div class="toc-item"><span class="toc-mark">{mark}</span>'
        f'<span class="toc-name">{_keep_words(name)}</span><span class="toc-page">{p}</span></div>'
        for mark, name, p in items
    )

    wm = WATERMARK_DIV if watermark else ""
    return f"""
<div>
{wm}  <div class="chapter-eyebrow">CONTENTS</div>
  <div class="chapter-title">목차</div>
  <div class="rule"></div>
  {rows}
</div>"""


def _build_body_html(data, sections, section_order, page_map, watermark=False):
    template_path = os.path.join(ASSETS_DIR, "template_body.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    parts = [_render_toc_block(section_order, page_map, watermark=watermark)]
    parts.append(_render_pillars_block(data, HANJA_NUMERALS[0], "pillars", watermark=watermark))
    for i, key in enumerate(section_order):
        chapter_num_str = _chapter_mark(i + 1)
        marker_id = f"sec_{i}_{key}"
        parts.append(_render_section_block(key, data, sections[key], chapter_num_str, marker_id, watermark=watermark))

    body_html = "\n".join(parts)
    return html.replace("{{BODY_PAGES}}", body_html)


def _run_wkhtmltopdf(args):
    subprocess.run(["wkhtmltopdf", *args], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _find_marker_pages(pdf_path, marker_ids):
    """
    pdftotext로 pdf_path의 각 페이지 텍스트를 확인해서, 각 marker_id가
    처음 등장하는 (1부터 시작하는) 로컬 페이지 번호를 찾는다.
    """
    info = subprocess.run(["pdfinfo", pdf_path], check=True, capture_output=True, text=True).stdout
    total_pages = 1
    for line in info.splitlines():
        if line.startswith("Pages:"):
            total_pages = int(line.split(":", 1)[1].strip())
            break

    remaining = set(marker_ids)
    found = {}
    for page in range(1, total_pages + 1):
        if not remaining:
            break
        text = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), pdf_path, "-"],
            check=True, capture_output=True, text=True
        ).stdout
        for marker_id in list(remaining):
            if f"PGMARK_{marker_id}_END" in text:
                found[marker_id] = page
                remaining.discard(marker_id)
    return found


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

    try:
        # ---- 1) 표지 렌더링 (여백 0, 별도 문서) ----------------------------
        cover_template_path = os.path.join(ASSETS_DIR, "template_cover.html")
        with open(cover_template_path, "r", encoding="utf-8") as f:
            cover_html = f.read()
        cover_html = cover_html.replace("{{NAME}}", _keep_words(name))
        cover_html = cover_html.replace("{{BIRTH_INFO}}", _keep_words(birth_info))
        cover_html = cover_html.replace("{{ISSUE_DATE}}", "2026")
        cover_html = cover_html.replace(
            "{{WATERMARK}}",
            '<div class="watermark"><div class="watermark-mark">SAMPLE · 미리보기</div></div>' if watermark else ""
        )
        with open(cover_html_path, "w", encoding="utf-8") as f:
            f.write(cover_html)

        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-size", "A4",
            "--margin-top", "0", "--margin-bottom", "0",
            "--margin-left", "0", "--margin-right", "0",
            "-q", cover_html_path, cover_pdf_path,
        ])

        # ---- 2) 본문 1차 렌더링 (목차 페이지번호는 아직 모름 → 마커만 심음) ----
        body_pass1_html = _build_body_html(data, sections, section_order, page_map={}, watermark=watermark)
        with open(body_pass1_html_path, "w", encoding="utf-8") as f:
            f.write(body_pass1_html)

        footer_path = os.path.join(ASSETS_DIR, "footer.html")
        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-size", "A4",
            "--margin-top", BODY_MARGIN_TOP, "--margin-bottom", BODY_MARGIN_BOTTOM,
            "--margin-left", BODY_MARGIN_LEFT, "--margin-right", BODY_MARGIN_RIGHT,
            "-q", body_pass1_html_path,
            "--footer-html", footer_path,
            body_pass1_pdf_path,
        ])

        # ---- 3) 마커가 실제로 몇 페이지에 찍혔는지 확인 ------------------------
        marker_ids = ["pillars"] + [f"sec_{i}_{key}" for i, key in enumerate(section_order)]
        local_pages = _find_marker_pages(body_pass1_pdf_path, marker_ids)
        # 표지(cover.pdf)가 항상 1페이지를 차지하므로, 실제 최종 문서에서의
        # 페이지 번호는 본문 내 로컬 페이지 번호 + 1 이다.
        page_map = {marker_id: local_page + 1 for marker_id, local_page in local_pages.items()}

        # ---- 4) 본문 최종 렌더링 (목차에 실제 페이지번호 반영) -----------------
        body_final_html = _build_body_html(data, sections, section_order, page_map=page_map, watermark=watermark)
        with open(body_final_html_path, "w", encoding="utf-8") as f:
            f.write(body_final_html)

        _run_wkhtmltopdf([
            "--encoding", "utf-8", "--enable-local-file-access",
            "--page-size", "A4",
            "--margin-top", BODY_MARGIN_TOP, "--margin-bottom", BODY_MARGIN_BOTTOM,
            "--margin-left", BODY_MARGIN_LEFT, "--margin-right", BODY_MARGIN_RIGHT,
            "--page-offset", "1",
            "-q", body_final_html_path,
            "--footer-html", footer_path,
            body_final_pdf_path,
        ])

        # ---- 5) 표지 + 본문 합치기 --------------------------------------------
        subprocess.run(["pdfunite", cover_pdf_path, body_final_pdf_path, output_pdf], check=True)

    finally:
        for p in [cover_html_path, cover_pdf_path, body_pass1_html_path, body_pass1_pdf_path,
                  body_final_html_path, body_final_pdf_path]:
            if os.path.exists(p):
                os.remove(p)

    print(f"완성: {output_pdf}")


if __name__ == "__main__":
    data = calculate_saju(1990, 5, 15, 10, 30, gender="M")
    sections = {
        "총론": "테스트 총론 문단입니다.\n\n두번째 문단.",
        "성격": "테스트 성격 문단입니다.\n\n두번째 문단.",
    }
    build_report(data, "테스트", "1990년생", sections, output_pdf="/tmp/dynamic_test.pdf")
