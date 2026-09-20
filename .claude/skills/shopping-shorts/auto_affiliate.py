#!/usr/bin/env python3
"""쇼핑쇼츠 자동 어필리에이트 파이프라인

쿠팡파트너스 상품 검색 → 딥링크 생성 → 인포크링크 자동 등록

사용법:
  python auto_affiliate.py "자석 이동 바퀴 캐스터"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coupang_deeplink import find_and_link
from inpock_register import register_link, ensure_playwright


def run_pipeline(keyword: str):
    print("=" * 50)
    print(f"🚀 어필리에이트 자동화 시작: '{keyword}'")
    print("=" * 50)

    # Step 1: 쿠팡파트너스 검색 + 딥링크 생성
    print("\n📦 [1/2] 쿠팡파트너스 딥링크 생성")
    print("-" * 40)
    result = find_and_link(keyword)

    if not result:
        print("\n❌ 쿠팡에서 상품을 찾지 못했습니다.")
        return None

    deeplink = result["deeplink"]
    product_name = result["productName"]
    price = result.get("productPrice", "")

    print(f"\n✅ 딥링크 생성 완료: {deeplink}")

    # Step 2: 인포크링크 자동 등록
    print(f"\n🔗 [2/2] 인포크링크 자동 등록")
    print("-" * 40)

    ensure_playwright()
    success = register_link(product_name, deeplink)

    # 결과 요약
    print("\n" + "=" * 50)
    if success:
        print("🎉 전체 파이프라인 완료!")
    else:
        print("⚠️  쿠팡 딥링크는 생성됨, 인포크링크는 수동 확인 필요")

    print(f"   상품명: {product_name}")
    print(f"   가격: {price}원")
    print(f"   딥링크: {deeplink}")
    print("=" * 50)

    return {
        "productName": product_name,
        "productPrice": price,
        "deeplink": deeplink,
        "inpock_registered": success,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python auto_affiliate.py '제품 키워드'")
        print("예시:  python auto_affiliate.py '자석 이동 바퀴 캐스터'")
        sys.exit(1)

    keyword = " ".join(sys.argv[1:])
    run_pipeline(keyword)
