#!/usr/bin/env python3
"""인포크링크 자동 링크 등록 (Playwright 브라우저 자동화)

사용법:
  python inpock_register.py "상품명" "https://link.coupang.com/..."

첫 실행 시 로그인 필요 → 이후 세션 유지됨.
"""

import sys
import os
import json
import time

INPOCK_URL = "https://link.inpock.co.kr"
SESSION_DIR = os.path.join(os.path.expanduser("~"), ".inpock_session")


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("Playwright 설치 중...")
        os.system(f"{sys.executable} -m pip install playwright")
        os.system(f"{sys.executable} -m playwright install chromium")
        return True


def register_link(product_name: str, deeplink_url: str, block_title: str = ""):
    from playwright.sync_api import sync_playwright

    title = block_title or f"🛒 {product_name}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=os.path.join(SESSION_DIR, "state.json")
            if os.path.exists(os.path.join(SESSION_DIR, "state.json"))
            else None
        )
        page = context.new_page()

        # 1. 인포크링크 접속
        print("🌐 인포크링크 접속 중...")
        page.goto(INPOCK_URL, wait_until="networkidle")
        time.sleep(2)

        # 2. 로그인 확인
        if _needs_login(page):
            print("\n🔑 로그인이 필요합니다.")
            print("   브라우저에서 로그인해주세요. (카카오/네이버/구글)")
            print("   로그인 완료 후 자동으로 진행됩니다...\n")

            _click_login(page)
            _wait_for_login(page)

            os.makedirs(SESSION_DIR, exist_ok=True)
            context.storage_state(path=os.path.join(SESSION_DIR, "state.json"))
            print("✅ 로그인 완료! 세션 저장됨.\n")

        # 3. 편집 페이지로 이동
        print("📝 편집 페이지 이동 중...")
        _go_to_editor(page)
        time.sleep(2)

        # 4. 링크 블록 추가
        print(f"🔗 링크 블록 추가: {title}")
        success = _add_link_block(page, title, deeplink_url)

        if success:
            # 세션 저장
            os.makedirs(SESSION_DIR, exist_ok=True)
            context.storage_state(path=os.path.join(SESSION_DIR, "state.json"))

            print(f"\n✅ 인포크링크 등록 완료!")
            print(f"   제목: {title}")
            print(f"   URL: {deeplink_url}")
        else:
            print("\n⚠️  자동 등록에 실패했습니다.")
            print("   브라우저가 열려 있으니 수동으로 등록해주세요.")
            print(f"   링크: {deeplink_url}")
            input("\n   등록 완료 후 Enter를 눌러주세요...")

        browser.close()
        return success


def _needs_login(page) -> bool:
    """로그인 필요 여부 확인"""
    try:
        login_indicators = [
            page.locator("text=로그인"),
            page.locator("text=시작하기"),
            page.locator("text=Sign in"),
            page.locator("text=Log in"),
        ]
        for indicator in login_indicators:
            if indicator.first.is_visible(timeout=2000):
                return True
    except Exception:
        pass

    try:
        dashboard_indicators = [
            page.locator("text=블록 추가"),
            page.locator("text=내 링크"),
            page.locator("text=편집"),
            page.locator("text=대시보드"),
        ]
        for indicator in dashboard_indicators:
            if indicator.first.is_visible(timeout=2000):
                return False
    except Exception:
        pass

    return True


def _click_login(page):
    """로그인 버튼 클릭"""
    selectors = [
        "text=로그인",
        "text=시작하기",
        "text=Sign in",
        "a[href*='login']",
        "button:has-text('로그인')",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                el.click()
                return
        except Exception:
            continue


def _wait_for_login(page, timeout_sec=120):
    """로그인 완료 대기"""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            indicators = [
                page.locator("text=블록 추가"),
                page.locator("text=내 링크"),
                page.locator("text=편집"),
                page.locator("text=대시보드"),
                page.locator("[class*='dashboard']"),
                page.locator("[class*='editor']"),
            ]
            for indicator in indicators:
                if indicator.first.is_visible(timeout=1000):
                    return True
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("로그인 시간 초과 (2분)")


def _go_to_editor(page):
    """편집/대시보드 페이지로 이동"""
    editor_urls = [
        f"{INPOCK_URL}/admin",
        f"{INPOCK_URL}/editor",
        f"{INPOCK_URL}/dashboard",
        f"{INPOCK_URL}/manage",
    ]

    for url in editor_urls:
        try:
            page.goto(url, wait_until="networkidle", timeout=5000)
            time.sleep(1)
            if not _needs_login(page):
                return
        except Exception:
            continue

    edit_selectors = [
        "text=편집",
        "text=관리",
        "text=내 링크",
        "text=대시보드",
        "a[href*='admin']",
        "a[href*='editor']",
        "a[href*='manage']",
    ]
    for sel in edit_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                el.click()
                page.wait_for_load_state("networkidle")
                return
        except Exception:
            continue


def _add_link_block(page, title: str, url: str) -> bool:
    """링크 블록 추가"""

    # 블록 추가 버튼 클릭
    add_selectors = [
        "text=블록 추가",
        "text=추가",
        "text=Add block",
        "text=Add",
        "button:has-text('추가')",
        "button:has-text('블록')",
        "[class*='add-block']",
        "[class*='addBlock']",
        "[data-testid*='add']",
    ]

    clicked = False
    for sel in add_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                time.sleep(1)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        # + 버튼 찾기
        try:
            plus = page.locator("button").filter(has_text="+").first
            if plus.is_visible(timeout=2000):
                plus.click()
                time.sleep(1)
                clicked = True
        except Exception:
            pass

    if not clicked:
        print("⚠️  '블록 추가' 버튼을 찾지 못했습니다.")
        return False

    # 링크 블록 타입 선택
    link_type_selectors = [
        "text=링크",
        "text=Link",
        "text=링크 블록",
        "[data-type='link']",
    ]

    for sel in link_type_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                time.sleep(1)
                break
        except Exception:
            continue

    # URL 입력
    url_filled = False
    url_selectors = [
        "input[placeholder*='URL']",
        "input[placeholder*='url']",
        "input[placeholder*='링크']",
        "input[placeholder*='주소']",
        "input[placeholder*='http']",
        "input[type='url']",
        "input[name*='url']",
        "input[name*='link']",
    ]

    for sel in url_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(url)
                el.press("Enter")
                time.sleep(2)
                url_filled = True
                break
        except Exception:
            continue

    if not url_filled:
        # 모든 input 중에서 빈 것 찾기
        try:
            inputs = page.locator("input:visible")
            for i in range(inputs.count()):
                inp = inputs.nth(i)
                if inp.input_value() == "":
                    inp.fill(url)
                    inp.press("Tab")
                    time.sleep(2)
                    url_filled = True
                    break
        except Exception:
            pass

    if not url_filled:
        print("⚠️  URL 입력 필드를 찾지 못했습니다.")
        return False

    # 제목 수정 (자동 입력된 제목 → 커스텀 제목으로 변경)
    title_selectors = [
        "input[placeholder*='제목']",
        "input[placeholder*='타이틀']",
        "input[placeholder*='Title']",
        "input[name*='title']",
        "input[name*='name']",
        "[contenteditable='true']",
    ]

    for sel in title_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill("")
                el.fill(title)
                time.sleep(1)
                break
        except Exception:
            continue

    # 저장 버튼 클릭
    save_selectors = [
        "text=저장",
        "text=Save",
        "text=완료",
        "text=확인",
        "text=적용",
        "button:has-text('저장')",
        "button:has-text('완료')",
        "button[type='submit']",
    ]

    for sel in save_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                time.sleep(2)
                break
        except Exception:
            continue

    return True


if __name__ == "__main__":
    ensure_playwright()

    if len(sys.argv) < 3:
        print("사용법: python inpock_register.py '상품명' 'https://딥링크URL'")
        print("예시:  python inpock_register.py '자석 이동 바퀴 캐스터' 'https://link.coupang.com/...'")
        sys.exit(1)

    product_name = sys.argv[1]
    deeplink_url = sys.argv[2]

    register_link(product_name, deeplink_url)
