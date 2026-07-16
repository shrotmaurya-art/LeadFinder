import sys

from playwright.sync_api import sync_playwright

def main() -> int:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://example.com", timeout=15000)
            title = page.title()
            browser.close()

        if "Example" in title:
            print("[PASS] Playwright: navigated to example.com, title contains 'Example'")
            return 0
        print(f"[FAIL] Playwright: title was '{title}', expected it to contain 'Example'")
        return 1
    except Exception as e:
        print(f"[FAIL] Playwright: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
