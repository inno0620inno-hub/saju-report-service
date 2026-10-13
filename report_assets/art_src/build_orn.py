# -*- coding: utf-8 -*-
"""PDF 글자 층에서 쓰는 장식 PNG(투명 배경) 생성기 — 개발용, 결과물만 저장소(report_assets/orn/)에 커밋.

wkhtmltopdf(구형 엔진)는 PNG 알파·border-image(9분할)를 지원하지만 최신 CSS 효과는 못 쓰므로,
금박 그라데이션·글로우가 필요한 장식은 여기서 Chrome으로 미리 그려 둔다.
  divider.png  : 장 도입/목차 구분선 (선 - 마름모 - 선)
  medal.png    : 장 번호를 얹는 메달(이중 금 고리 + 구슬 + 꽃잎)
  frame.png    : 삽화·콜아웃용 9분할 액자 (모서리 연꽃잎, 변은 곧은 선)
  end.png      : 맺음 장식
사용: python build_orn.py [출력폴더]
"""
import asyncio
import math
import os
import sys

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "orn")

GRAD = """<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{h}"><stop offset="0" stop-color="#fff3c4"/><stop offset=".5" stop-color="#e3bd62"/><stop offset="1" stop-color="#b8892c"/></linearGradient>
<linearGradient id="gh" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="0"><stop offset="0" stop-color="#b8892c" stop-opacity="0"/><stop offset=".18" stop-color="#d4aa3a"/><stop offset=".5" stop-color="#fff3c4"/><stop offset=".82" stop-color="#d4aa3a"/><stop offset="1" stop-color="#b8892c" stop-opacity="0"/></linearGradient>
<filter id="b" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>"""


def dia(cx, cy, w, h, extra=""):
    return f'<path d="M{cx} {cy - h / 2}L{cx + w / 2} {cy}L{cx} {cy + h / 2}L{cx - w / 2} {cy}Z" {extra}/>'


def divider(w=1400, h=84):
    cx, cy = w / 2, h / 2
    s = f'<g filter="url(#b)" opacity=".5"><line x1="40" y1="{cy}" x2="{cx - 70}" y2="{cy}" stroke="url(#gh)" stroke-width="4"/><line x1="{cx + 70}" y1="{cy}" x2="{w - 40}" y2="{cy}" stroke="url(#gh)" stroke-width="4"/></g>'
    s += f'<line x1="40" y1="{cy}" x2="{cx - 70}" y2="{cy}" stroke="url(#gh)" stroke-width="2.4"/><line x1="{cx + 70}" y1="{cy}" x2="{w - 40}" y2="{cy}" stroke="url(#gh)" stroke-width="2.4"/>'
    s += f'<line x1="140" y1="{cy + 9}" x2="{cx - 100}" y2="{cy + 9}" stroke="url(#gh)" stroke-width="1" opacity=".7"/><line x1="{cx + 100}" y1="{cy + 9}" x2="{w - 140}" y2="{cy + 9}" stroke="url(#gh)" stroke-width="1" opacity=".7"/>'
    s += dia(cx, cy, 44, 44, 'fill="none" stroke="url(#g)" stroke-width="3"') + dia(cx, cy, 22, 22, 'fill="url(#g)"')
    for d in (-1, 1):
        s += dia(cx + d * 62, cy, 14, 14, 'fill="url(#g)"') + dia(cx + d * 92, cy, 9, 9, 'fill="url(#g)"')
        s += f'<circle cx="{cx + d * 118}" cy="{cy}" r="3.4" fill="url(#g)"/>'
    return s, w, h


def medal(S=600):
    c = S / 2
    s = f'<circle cx="{c}" cy="{c}" r="236" fill="none" stroke="url(#g)" stroke-width="22" opacity=".42" filter="url(#b)"/>'
    for i in range(16):                                         # 바깥 꽃잎(뾰족한 잎 16장)
        a = i * 22.5
        s += f'<path d="M{c} {c - 292}C{c + 22} {c - 268} {c + 22} {c - 244} {c} {c - 226}C{c - 22} {c - 244} {c - 22} {c - 268} {c} {c - 292}Z" transform="rotate({a} {c} {c})" fill="rgba(212,175,90,.14)" stroke="url(#g)" stroke-width="2"/>'
    s += f'<circle cx="{c}" cy="{c}" r="228" fill="rgba(10,6,24,.92)" stroke="url(#g)" stroke-width="7"/>'
    s += f'<circle cx="{c}" cy="{c}" r="212" fill="none" stroke="url(#g)" stroke-width="2.4"/>'
    s += f'<circle cx="{c}" cy="{c}" r="196" fill="none" stroke="url(#g)" stroke-width="5" stroke-dasharray="0.1 18" stroke-linecap="round" opacity=".9"/>'
    s += f'<circle cx="{c}" cy="{c}" r="176" fill="none" stroke="url(#g)" stroke-width="1.6" opacity=".8"/>'
    for i in range(8):                                          # 8방위 마름모
        a = math.radians(i * 45 - 90)
        s += dia(c + 228 * math.cos(a), c + 228 * math.sin(a), 18, 18, 'fill="url(#g)" stroke="#0a0614" stroke-width="3"')
    return s, S, S


def frame(S=240, C=84):
    """9분할 액자 원본: 모서리 C×C 영역에만 장식, 변 영역은 곧은 선(늘려도 안 깨짐)"""
    o, i = 6, 16                                                # 바깥선/안쪽선 위치
    s = f'<rect x="{o}" y="{o}" width="{S - 2 * o}" height="{S - 2 * o}" fill="none" stroke="url(#g)" stroke-width="4"/>'
    s += f'<rect x="{i}" y="{i}" width="{S - 2 * i}" height="{S - 2 * i}" fill="none" stroke="url(#g)" stroke-width="1.6" opacity=".85"/>'
    # 모서리 연꽃 부채(좌상단 기준 4방향)
    petal = lambda ln, wd: f"M0 0C{ln * .3:.1f} {-wd} {ln * .78:.1f} {-wd * .9:.1f} {ln:.1f} 0C{ln * .78:.1f} {wd * .9:.1f} {ln * .3:.1f} {wd} 0 0Z"
    corner = ""
    ox, oy = 30, 30
    for deg, ln in [(0, 44), (22.5, 36), (45, 50), (67.5, 36), (90, 44)]:
        corner += f'<path d="{petal(ln, 8)}" transform="translate({ox} {oy}) rotate({deg})" fill="rgba(212,175,90,.2)" stroke="url(#g)" stroke-width="1.8"/>'
    corner += dia(o, o, 20, 20, 'fill="url(#g)"') + dia(o, o, 8, 8, 'fill="#0a0614"')
    corner += f'<circle cx="{ox}" cy="{oy}" r="5" fill="url(#g)"/><circle cx="{ox}" cy="{oy}" r="2" fill="#0a0614"/>'
    for t in ["", f"translate({S} 0) scale(-1 1)", f"translate({S} {S}) scale(-1 -1)", f"translate(0 {S}) scale(1 -1)"]:
        s += f'<g {f"transform=" + chr(34) + t + chr(34) if t else ""}>{corner}</g>'
    return s, S, S


def end_orn(w=1000, h=140):
    cx, cy = w / 2, h / 2
    s = f'<g filter="url(#b)" opacity=".5"><circle cx="{cx}" cy="{cy}" r="46" fill="none" stroke="url(#g)" stroke-width="4"/></g>'
    s += f'<circle cx="{cx}" cy="{cy}" r="46" fill="rgba(10,6,24,.9)" stroke="url(#g)" stroke-width="3"/><circle cx="{cx}" cy="{cy}" r="38" fill="none" stroke="url(#g)" stroke-width="1.2"/>'
    s += dia(cx, cy, 30, 30, 'fill="url(#g)"') + dia(cx, cy, 12, 12, 'fill="#0a0614"')
    for d in (-1, 1):
        s += f'<line x1="{cx + d * 64}" y1="{cy}" x2="{cx + d * 420}" y2="{cy}" stroke="url(#gh)" stroke-width="2.4"/>'
        s += f'<line x1="{cx + d * 100}" y1="{cy + 9}" x2="{cx + d * 340}" y2="{cy + 9}" stroke="url(#gh)" stroke-width="1" opacity=".7"/>'
        for k, off in enumerate((84, 112, 146)):
            s += dia(cx + d * off, cy, 12 - k * 2, 12 - k * 2, 'fill="url(#g)"')
    return s, w, h


async def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = {"divider": divider(), "medal": medal(), "frame": frame(), "end": end_orn()}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, (inner, w, h) in jobs.items():
            ctx = await b.new_context(viewport={"width": int(w), "height": int(h)}, device_scale_factor=1)
            page = await ctx.new_page()
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{GRAD.format(w=w, h=h)}</defs>{inner}</svg>'
            await page.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            path = os.path.join(OUT, f"{name}.png")
            await page.screenshot(path=path, omit_background=True, clip={"x": 0, "y": 0, "width": int(w), "height": int(h)})
            print(name, int(w), "x", int(h), os.path.getsize(path) // 1024, "KB")
            await ctx.close()
        await b.close()


asyncio.run(main())
