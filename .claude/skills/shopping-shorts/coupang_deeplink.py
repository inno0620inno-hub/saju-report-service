#!/usr/bin/env python3
"""쿠팡파트너스 API - 상품 검색 & 딥링크 생성"""

import os
import sys
import time
import hmac
import hashlib
import json
import urllib.request
import urllib.parse

DOMAIN = "https://api-gateway.coupang.com"
SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"

ACCESS_KEY = os.environ.get("COUPANG_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("COUPANG_SECRET_KEY", "")


def generate_hmac(method, url):
    path, *query = url.split("?")
    os.environ["TZ"] = "GMT+0"
    dt = time.strftime("%y%m%d") + "T" + time.strftime("%H%M%S") + "Z"
    message = dt + method + path + (query[0] if query else "")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={dt}, signature={signature}"


def search_products(keyword, limit=5):
    params = urllib.parse.urlencode({
        "keyword": keyword,
        "limit": limit,
    })
    url = f"{SEARCH_PATH}?{params}"
    authorization = generate_hmac("GET", url)

    req = urllib.request.Request(
        f"{DOMAIN}{url}",
        headers={"Authorization": authorization},
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("data", {}).get("productData", [])


def create_deeplink(product_url):
    url = DEEPLINK_PATH
    authorization = generate_hmac("POST", url)

    body = json.dumps({
        "coupangUrls": [product_url],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{DOMAIN}{url}",
        data=body,
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("data", [])


def find_and_link(keyword):
    if not ACCESS_KEY or not SECRET_KEY:
        print("ERROR: COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    print(f"🔍 '{keyword}' 검색 중...")
    products = search_products(keyword)

    if not products:
        print("상품을 찾지 못했습니다.")
        return None

    print(f"\n📦 검색 결과 ({len(products)}개):")
    for i, p in enumerate(products):
        print(f"  {i+1}. {p.get('productName', 'N/A')}")
        print(f"     가격: {p.get('productPrice', 'N/A')}원")
        print(f"     URL: {p.get('productUrl', 'N/A')}")
        print()

    best = products[0]
    product_url = best.get("productUrl", "")

    print(f"🔗 딥링크 생성 중... ({best.get('productName', '')[:30]})")
    deeplinks = create_deeplink(product_url)

    if deeplinks:
        deeplink_url = deeplinks[0].get("shortenUrl", "")
        print(f"\n✅ 딥링크 생성 완료!")
        print(f"   상품명: {best.get('productName', 'N/A')}")
        print(f"   가격: {best.get('productPrice', 'N/A')}원")
        print(f"   딥링크: {deeplink_url}")
        return {
            "productName": best.get("productName"),
            "productPrice": best.get("productPrice"),
            "productUrl": product_url,
            "deeplink": deeplink_url,
            "allProducts": products,
        }

    print("딥링크 생성 실패")
    return None


if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("검색 키워드: ")
    result = find_and_link(keyword)
    if result:
        print(f"\n📋 유튜브 설명글에 넣을 링크:")
        print(f"🛒 구매링크: {result['deeplink']}")
