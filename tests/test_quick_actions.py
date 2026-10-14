import sys
sys.stdout.reconfigure(encoding="utf-8")

import urllib.request
import pytest
from playwright.sync_api import sync_playwright
import time

def test_quick_actions():
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=0.5):
            pass
    except Exception:
        pytest.skip("Local test server is not running on http://localhost:8000")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        console_logs = []
        page_errors = []
        network_calls = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("response", lambda resp: network_calls.append(f"{resp.request.method} {resp.url} -> {resp.status}"))

        print("Navigating to login page...")
        page.goto("http://localhost:8000/admin/login.html")
        page.fill("#username-input", "admin")
        page.fill("#password-input", "admin123")
        page.click("#login-submit-btn")
        time.sleep(1)

        print("Navigating to dashboard...")
        page.goto("http://localhost:8000/admin/#dashboard")
        time.sleep(2)

        # 1. Test Quick Book Appointment Modal
        print("Testing Quick Book Appointment button...")
        page.click("#quick-book-appt-btn")
        
        # Wait up to 5 seconds for modal to open
        for _ in range(10):
            time.sleep(0.5)
            modal_backdrop = page.query_selector("#app-modal-backdrop")
            if modal_backdrop and "open" in (modal_backdrop.get_attribute("class") or ""):
                break

        modal_backdrop = page.query_selector("#app-modal-backdrop")
        modal_title = page.query_selector("#app-modal-title")
        is_modal_open = "open" in (modal_backdrop.get_attribute("class") or "")
        print(f"Book Modal Open: {is_modal_open}, Title: {modal_title.inner_text() if modal_title else ''}")

        print("\n--- Console Logs ---")
        for l in console_logs:
            print(l)

        print("\n--- Page Errors ---")
        for e in page_errors:
            print(e)

        print("\n--- Network Calls after button click ---")
        for c in network_calls[-10:]:
            print(c)

        assert is_modal_open, "Book Appointment modal failed to open!"

        # Close modal
        page.click("#app-modal-close-btn")
        time.sleep(0.5)

        # 2. Test Quick Register Patient Modal
        print("Testing Quick Register Patient button...")
        page.click("#quick-add-patient-btn")
        for _ in range(10):
            time.sleep(0.5)
            if modal_backdrop and "open" in (modal_backdrop.get_attribute("class") or ""):
                break

        is_modal_open = "open" in (modal_backdrop.get_attribute("class") or "")
        print(f"Register Patient Modal Open: {is_modal_open}, Title: {modal_title.inner_text() if modal_title else ''}")
        assert is_modal_open, "Register Patient modal failed to open!"

        # Close modal
        page.click("#app-modal-close-btn")
        time.sleep(0.5)

        browser.close()
        print("Quick actions test PASSED successfully!")

if __name__ == "__main__":
    test_quick_actions()

