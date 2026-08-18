# -*- coding: utf-8 -*-
"""
build_report.py
saju_core 계산결과 + AI 해석문(섹션 텍스트) + 선택된 섹션 목록을 받아서
template.html에 동적으로 페이지를 조립해 최종 PDF 리포트를 생성한다.

상품(product)마다 섹션 개수/종류가 다르므로, 목차·챕터 번호·페이지 번호를
전부 파이썬에서 동적으로 계산해서 만든다.
"""

import subprocess
import os
from saju_core import calculate_saju
from report_prompts import SECTION_SPECS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

OHENG_COLOR_VAR = {"목": "wood", "화": "fire", "토": "earth", "금": "metal", "수": "water"}
HANJA_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]


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
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in parts)


CALLOUTS = {
    "재물운": "본 리포트는 특정 투자처나 종목을 추천하지 않으며, 참고용 성향 분석입니다.",
    "건강운": "본 리포트는 의학적 진단이 아닙니다. 정확한 건강 상태는 반드시 의료 전문가와 상담하시기 바랍니다.",
}


def _render_pillars_page(data, chapter_num_str, page_num):
    return f"""
<div class="page">
<div class="page-inner">
  <div class="chapter-mark">{chapter_num_str}</div>
  <div class="chapter-eyebrow">THE FOUR PILLARS</div>
  <div class="chapter-title">사주 원국</div>
  <div class="chapter-title-sub">태어난 순간의 하늘과 땅 — 여덟 글자</div>
  <div class="rule"></div>
  <div class="myeongsik">
    {render_pillar_cards(data)}
  </div>
  <div class="body-text">
    <p>이 사주의 일간(본인을 상징하는 글자)은 {data['day_master']}입니다. 오행 중
    {max(data['oheng_distribution'], key=data['oheng_distribution'].get)}의 기운이 상대적으로
    강하게 나타나며, 이는 이후 섹션에서 다루는 성격과 흐름의 바탕이 됩니다.</p>
  </div>
  <div class="chapter-title-sub" style="margin-top:30px; font-size:13px;">오행(五行) 분포</div>
  <div class="oheng-bars">
    {render_oheng_bars(data)}
  </div>
  <div class="page-num">{page_num:03d}</div>
</div>
</div>"""


def _render_section_page(section_key, data, section_text, chapter_num_str, page_num):
    spec = SECTION_SPECS[section_key]
    extra_visual = ""
    if section_key == "대운흐름":
        extra_visual = f"""
  <div class="chapter-title-sub" style="margin-top:-10px;">{data['daeun']['direction']} · {data['daeun']['daeun_start_age']}세부터 시작</div>
  <div class="daeun-timeline">
    {render_daeun_steps(data)}
  </div>"""
        subtitle = ""  # 위 extra_visual에서 이미 부제 역할을 하므로 중복 방지
    else:
        subtitle = f'<div class="chapter-title-sub">{spec["subtitle"]}</div>'

    callout_html = ""
    if section_key in CALLOUTS:
        callout_html = f'<div class="callout">{CALLOUTS[section_key]}</div>'

    return f"""
<div class="page">
<div class="page-inner">
  <div class="chapter-mark">{chapter_num_str}</div>
  <div class="chapter-eyebrow">{spec['eyebrow']}</div>
  <div class="chapter-title">{spec['title']}</div>
  {subtitle}
  <div class="rule"></div>
  {extra_visual}
  <div class="body-text">
    {paragraphs(section_text)}
  </div>
  {callout_html}
  <div class="page-num">{page_num:03d}</div>
</div>
</div>"""


def _render_toc_page(section_keys, page_num):
    items = []
    items.append(('一', "사주 원국 · 오행 분포", 3))
    page = 4
    for i, key in enumerate(section_keys):
        items.append((HANJA_NUMERALS[i + 1], SECTION_SPECS[key]["title"], page))
        page += 1

    rows = "\n".join(
        f'<div class="toc-item"><span class="toc-mark">{mark}</span>'
        f'<span class="toc-name">{name}</span><span class="toc-page">{p:02d}</span></div>'
        for mark, name, p in items
    )

    return f"""
<div class="page">
<div class="page-inner">
  <div class="chapter-eyebrow">CONTENTS</div>
  <div class="chapter-title">목차</div>
  <div class="rule"></div>
  {rows}
  <div class="page-num">{page_num:03d}</div>
</div>
</div>"""


def build_report(data, name, birth_info, sections, section_order=None,
                  product_name="사주 명식 리포트", output_pdf="saju_report.pdf"):
    """
    sections: {section_key: 해석문_텍스트} 딕셔너리
    section_order: 섹션을 표시할 순서 (list of keys). None이면 sections의 키 순서 사용.
    """
    if section_order is None:
        section_order = list(sections.keys())

    template_path = os.path.join(SCRIPT_DIR, "report_assets", "template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # ---- 본문 페이지들 동적 조립 ----
    body_parts = []
    body_parts.append(_render_toc_page(section_order, page_num=2))
    body_parts.append(_render_pillars_page(data, HANJA_NUMERALS[0], page_num=3))

    page_num = 4
    for i, key in enumerate(section_order):
        chapter_num_str = HANJA_NUMERALS[i + 1] if (i + 1) < len(HANJA_NUMERALS) else str(i + 2)
        body_parts.append(_render_section_page(key, data, sections[key], chapter_num_str, page_num))
        page_num += 1

    replacements = {
        "{{NAME}}": name,
        "{{BIRTH_INFO}}": birth_info,
        "{{ISSUE_DATE}}": "2026",
        "{{BODY_PAGES}}": "\n".join(body_parts),
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
        "총론": "테스트 총론 문단입니다.\n\n두번째 문단.",
        "성격": "테스트 성격 문단입니다.\n\n두번째 문단.",
    }
    build_report(data, "테스트", "1990년생", sections, output_pdf="/tmp/dynamic_test.pdf")
