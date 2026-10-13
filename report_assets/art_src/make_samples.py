# -*- coding: utf-8 -*-
"""신청 폼에 보여 줄 '샘플 리포트 화면'을 만든다 (개발용 — 서버 런타임에서는 쓰지 않음).

가상 인물 '홍길동 · 1990-05-21 13:30 · 양력 · 남'의 샘플 PDF를 실제 파이프라인(build_report)으로 만든 뒤,
고른 쪽을 JPG로 내보낸다 → webapp/assets/pdf_*.jpg  (신청 폼 웹툰의 "이렇게 전해 드립니다" 갤러리가 사용).

- 사주 카드·오행 분포는 saju_core가 계산한 실제 값, 풀이 문장은 이 파일에 직접 쓴 샘플 문단(서로 다른 문장).
- 필요: wkhtmltopdf, pdftotext 가 PATH에 있어야 함 + pip install pymupdf pillow pypdf
사용: python make_samples.py [출력폴더=../../webapp/assets] [샘플PDF=sample_report.pdf]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

import pymupdf
from PIL import Image

import build_report
from saju_core import calculate_saju
from report_prompts import SECTION_SPECS

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "webapp", "assets")
PDF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "sample_report.pdf")
VER = "v1"                               # 파일명 접미사(브라우저 캐시 우회 — 그림을 바꾸면 올릴 것)

SAMPLE = {
    "총론": """자, 자리에 편하게 앉아 보세요. 이 사주의 큰 그림부터 짚어 드리겠습니다.
태어난 날의 글자가 을유(乙酉)인데요, 쉽게 말해 바위 틈에서도 뿌리를 내리는 덩굴 같은 사람입니다. 겉으로는 부드럽고 유연해 보이지만, 한번 방향을 정하면 쉽게 꺾이지 않는 끈기가 있습니다.

이 사주에는 쇠의 기운, 금(金)이 유난히 많습니다. 경오(庚午), 신사(辛巳), 을유(乙酉) 세 군데에 금이 깔려 있으니, 어릴 때부터 '잘해야 한다'는 압박 속에서 자라셨을 가능성이 큽니다. 그 압박이 지금의 꼼꼼함과 책임감을 만들었지요.

다만 금이 강하면 나무는 가지치기를 많이 당합니다. 그래서 스스로를 자주 다그치고, 남의 평가에 마음이 흔들릴 때가 있습니다. 이 부분, 꽤 정확하실 겁니다.

좋은 소식도 있습니다. 불의 기운이 곳곳에 숨어 있어서, 쇠를 녹여 쓸모 있는 도구로 바꿔 내는 힘이 있습니다. 압박을 재능으로 바꾸는 사주라는 뜻입니다. 이 흐름을 알고 쓰느냐 모르고 쓰느냐에 따라 같은 사주도 전혀 다른 삶이 됩니다.

이제부터 성격, 대운의 흐름, 재물까지 한 장씩 펼쳐 드리겠습니다. 천천히 따라오시면 다 보입니다.""",
    "성격": """겉모습과 속마음이 조금 다른 분입니다. 처음 만난 사람에게는 온화하고 배려 깊은 인상을 주지만, 속으로는 모든 것을 한 번 더 따져 보는 신중함이 있습니다.

첫 번째 강점은 '꾸준함'입니다. 화려하게 시작하지는 않아도 끝까지 가는 쪽이고, 그래서 시간이 갈수록 주변의 신뢰가 쌓입니다. 사람들은 당신의 말 한마디에 무게를 느낍니다.

두 번째는 '눈치와 감각'입니다. 분위기가 바뀌는 순간을 남들보다 먼저 알아채고, 갈등이 커지기 전에 조용히 정리하는 재주가 있습니다. 모임에서 말수가 적어도 존재감이 큰 이유가 여기에 있습니다.

세 번째 강점은 '쓸모를 만드는 힘'입니다. 어려운 상황에서도 방법을 찾아내는 편이라, 위기 때 오히려 빛나는 분입니다.

반대로 조심할 점도 있습니다. 혼자 끌어안는 습관이 쌓이면 마음이 먼저 지칩니다. 도움을 청하는 연습, 거절하는 연습을 의식적으로 해 보세요. 이 사주에서는 그것이 가장 좋은 보약입니다.""",
    "대운흐름": """대운은 10년 단위로 바뀌는 큰 계절입니다. 지금 걸어가는 계절이 어디쯤인지 알면, 서두를 때와 쉬어 갈 때가 보입니다.

앞선 대운은 준비의 시간이었습니다. 눈에 띄는 성과가 없어도 뿌리를 내리는 시기였지요. 다음 대운부터는 그 뿌리 위에 잎이 나기 시작합니다.

올라가는 구간에서는 새로운 제안이 늘어납니다. 모두 받아들일 필요는 없습니다. 순서를 정하고 하나씩 잡으면 흐름이 오래 갑니다.

쉬어 가는 구간에는 억지로 확장하지 마세요. 그 시기에 쌓아 둔 실력이 다음 계절의 밑천이 됩니다.""",
    "재물운": """돈은 들어오는 길과 새는 구멍이 따로 있습니다. 이 사주는 크게 한 번에 버는 쪽보다 꾸준히 모아서 불리는 쪽이 맞습니다.

들어오는 때를 알면 새는 구멍도 막기 쉬워집니다. 특히 사람 때문에 나가는 돈, 체면 때문에 쓰는 돈을 조심하세요. 욕심보다 순서가 먼저입니다.

올해는 흐름이 바뀌는 시기라, 큰 결정은 하반기로 미루는 편이 이득입니다. 상반기에는 정리와 점검에 집중해 보세요.""",
}

def main():
    keys = list(SAMPLE.keys())
    assert all(k in SECTION_SPECS for k in keys), "SECTION_SPECS 키와 샘플 키가 다릅니다"
    data = calculate_saju(1990, 5, 21, 13, 30, gender="M")
    build_report.build_report(data, "홍길동", "1990년 5월 21일 13시 30분생 · 양력 · 남", SAMPLE,
                              section_order=keys, output_pdf=PDF, watermark=False)
    doc = pymupdf.open(PDF)
    print("샘플 PDF:", len(doc), "쪽,", os.path.getsize(PDF) // 1024, "KB")
    # 어떤 쪽이 무엇인지 찾기 (제목 글자로)
    def find(pred, start=0):
        for i in range(start, len(doc)):
            if pred(re.sub(r"\s+", "", doc[i].get_text())):      # 자간이 벌어진 영문 라벨(O V E R V I E W)도 찾도록 공백 제거
                return i
        return None
    pages = {
        "cover": 0,
        "pillars": find(lambda t: "년주" in t and "월주" in t and "일주" in t),
        "chapter": find(lambda t: "OVERVIEW" in t),
        "daeun": find(lambda t: "TEN-YEAR" in t),
        "wealth": find(lambda t: "WEALTH" in t),
    }
    print("선택 쪽(0부터):", pages)
    os.makedirs(OUT, exist_ok=True)
    for name, idx in pages.items():
        if idx is None:
            print("  !! 못 찾음:", name); continue
        pix = doc[idx].get_pixmap(dpi=82)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        path = os.path.join(OUT, f"pdf_{name}_{VER}.jpg")
        im.save(path, "JPEG", quality=80, optimize=True, subsampling=0)
        print("  ", os.path.basename(path), im.size, os.path.getsize(path) // 1024, "KB")


main()
