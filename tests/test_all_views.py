import sys
sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
import time

VIEWS_TO_TEST = [
    ("dashboard", "view-dashboard"),
    ("appointments", "view-appointments"),
    ("calendar", "view-calendar"),
    ("patients", "view-patients"),
    ("doctors", "view-doctors"),
    ("slots", "view-slots"),
    ("payments", "view-payments"),
    ("reports", "view-reports"),
    ("audit-logs", "view-audit-logs"),
    ("settings", "view-settings"),
]

def test_all_crm_views():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        console_logs = []
        page_errors = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("=== Step 1: Navigating to login page ===")
        page.goto("http://localhost:8000/admin/login.html", wait_until="networkidle")

        print("=== Step 2: Submitting login credentials ===")
        page.fill("#username-input", "admin")
        page.fill("#password-input", "admin123")
        page.click("#login-submit-btn")
        time.sleep(1)

        print("\n=== Step 3: Testing All 10 CRM Views ===")
        results = []

        for view_name, container_id in VIEWS_TO_TEST:
            url = f"http://localhost:8000/admin/#{view_name}"
            page.goto(url)
            time.sleep(1.5)  # Wait for view init and API fetch

            container = page.query_selector(f"#{container_id}")
            is_visible = container.is_visible() if container else False
            inner_html = container.inner_html().strip() if container else ""
            html_len = len(inner_html)

            # Check if navigation link is marked active
            active_nav = page.query_selector(f".nav-item[data-view='{view_name}'].active")
            is_nav_active = active_nav is not None

            status = "PASS" if (is_visible and html_len > 50 and is_nav_active) else "FAIL"
            results.append((view_name, container_id, is_visible, html_len, is_nav_active, status))
            print(f"[{status}] View: #{view_name:<12} | Container: #{container_id:<18} | Visible: {is_visible} | HTMLLen: {html_len:<6} | NavActive: {is_nav_active}")

        print("\n=== Console Logs Recorded ===")
        for log in console_logs:
            if "error" in log.lower():
                print("ERROR LOG:", log)

        print("\n=== Page Errors Recorded ===")
        for err in page_errors:
            print("PAGE ERROR:", err)

        browser.close()
        
        all_passed = all(r[-1] == "PASS" for r in results) and len(page_errors) == 0
        print(f"\nFinal Result: {'ALL VIEWS PASSED' if all_passed else 'SOME VIEWS FAILED'}")
        assert all_passed

if __name__ == "__main__":
    success = test_all_crm_views()
    sys.exit(0 if success else 1)

