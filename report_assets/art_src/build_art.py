# -*- coding: utf-8 -*-
"""PDF 배경 아트 생성기 (개발용 — 서버 런타임에서는 쓰지 않는다. 결과물만 저장소에 커밋)

art.html?m=cover|page|opener 를 Chrome(Playwright)으로 그려 → 필름 그레인을 입혀 밴딩을 막고
→ JPEG로 저장 → PyMuPDF로 1페이지 PDF(220×391.11mm)로 감싼다.
  결과: report_assets/art/cover.pdf, page.pdf, opener.pdf  (+ 미리보기 png)

사용: python build_art.py [출력폴더]   (필요: pip install playwright pillow pymupdf, playwright install chromium)
"""
import asyncio
import os
import sys

import pymupdf
from PIL import Image, ImageChops
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "art")
PAGES = sys.argv[2].split(",") if len(sys.argv) > 2 else ["cover", "page", "opener"]
DPR = float(os.environ.get('ART_DPR', 1.6))                      # 832×1478 CSS px × 1.6 ≈ 1331×2365 px (폰 화면에서 충분히 선명하면서 용량은 페이지당 ~300KB)
PT_W, PT_H = 220 / 25.4 * 72, 391.11 / 25.4 * 72   # 623.62 × 1108.7 pt (본문 PDF와 같은 크기)


def grain(im: Image.Image, strength: float = float(os.environ.get('ART_GRAIN', 2.0))) -> Image.Image:
    """어두운 그라데이션의 띠(밴딩)를 없애기 위한 아주 가는 노이즈."""
    noise = Image.effect_noise(im.size, 40).convert("L")           # 평균 128 정규분포
    noise = noise.point(lambda v: int(128 + (v - 128) * strength / 40))
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    # 128 기준 노이즈를 'soft add' 로 얹는다
    base = im.convert("RGB")
    plus = ImageChops.add(base, noise_rgb, scale=1.0, offset=-128)
    return plus


async def render(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 832, "height": 1478}, device_scale_factor=DPR)
        page = await ctx.new_page()
        for m in PAGES:
            await page.goto("file:///" + os.path.join(HERE, "art.html").replace("\\", "/") + f"?m={m}")
            await page.wait_for_function("document.title === 'ready'", timeout=30000)
            await page.wait_for_timeout(600)
            png = os.path.join(out_dir, f"{m}_raw.png")
            await page.screenshot(path=png, clip={"x": 0, "y": 0, "width": 832, "height": 1478})
            im = grain(Image.open(png))
            jpg = os.path.join(out_dir, f"{m}.jpg")
            im.save(jpg, "JPEG", quality=int(os.environ.get("ART_Q", 82)), subsampling=0, optimize=True)
            doc = pymupdf.open()
            pg = doc.new_page(width=PT_W, height=PT_H)
            pg.insert_image(pg.rect, filename=jpg)           # JPEG 그대로 삽입(재압축 없음)
            doc.save(os.path.join(out_dir, f"{m}.pdf"), deflate=True)
            doc.close()
            os.remove(png)
            print(m, im.size, os.path.getsize(jpg) // 1024, "KB jpg ->", os.path.getsize(os.path.join(out_dir, f"{m}.pdf")) // 1024, "KB pdf")
            os.remove(jpg)                                   # JPG는 PDF 안에 들어갔으니 지운다
        await b.close()


asyncio.run(render(OUT))
