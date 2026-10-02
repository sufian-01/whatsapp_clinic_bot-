import sys
import os
sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
import time
import json

def test_login_and_dashboard():
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

        print("=== Step 1: Navigating to login page ===")
        page.goto("http://localhost:8000/admin/login.html", wait_until="networkidle")

        print("=== Step 2: Logging in ===")
        page.fill("#username-input", "admin")
        page.fill("#password-input", "admin123")
        page.click("#login-submit-btn")

        # Wait for redirect
        time.sleep(1)
        if "login.html" in page.url:
            page.goto("http://localhost:8000/admin/#dashboard")
        
        # Wait up to 5 seconds for network activity to settle
        time.sleep(5)
        print(f"Post-login URL: {page.url}")

        print("\n--- Console Logs ---")
        for log in console_logs:
            print(log)

        print("\n--- Page Errors ---")
        for err in page_errors:
            print(err)

        print("\n--- Network Calls ---")
        for call in network_calls:
            if "api" in call:
                print(call)

        # Inspect DOM of #view-dashboard
        dashboard_el = page.query_selector("#view-dashboard")
        if dashboard_el:
            print(f"\n#view-dashboard is_visible: {dashboard_el.is_visible()}")
            print(f"InnerHTML length: {len(dashboard_el.inner_html())}")

        metric_cards = page.query_selector_all(".metric-card")
        print(f"\nNumber of metric cards rendered: {len(metric_cards)}")
        for idx, card in enumerate(metric_cards):
            print(f"Card {idx}: {card.inner_text().strip().replace(chr(10), ' | ')}")

        table_rows = page.query_selector_all("#today-appointments-tbody tr")
        print(f"\nToday appointments table rows: {len(table_rows)}")
        for idx, row in enumerate(table_rows):
            print(f"Row {idx}: {row.inner_text().strip().replace(chr(10), ' | ')}")

        recent_patients = page.query_selector_all(".recent-patient-item")
        print(f"\nRecent patient items: {len(recent_patients)}")
        for idx, p_item in enumerate(recent_patients):
            print(f"Patient {idx}: {p_item.inner_text().strip().replace(chr(10), ' | ')}")

        toast = page.query_selector(".toast")
        if toast:
            print(f"\nToast displayed: {toast.inner_text()}")

        page.screenshot(path="dashboard_screenshot.png")
        print("\nSaved screenshot to dashboard_screenshot.png")

        browser.close()

if __name__ == "__main__":
    test_login_and_dashboard()

