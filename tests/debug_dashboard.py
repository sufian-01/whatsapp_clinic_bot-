from playwright.sync_api import sync_playwright

def inspect_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_msgs = []
        page_errors = []
        failed_requests = []
        responses = []

        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("requestfailed", lambda r: failed_requests.append(f"{r.method} {r.url}: {r.failure}"))
        page.on("response", lambda r: responses.append(f"{r.request.method} {r.url} -> {r.status}"))

        print("1. Navigating to login...")
        page.goto("http://127.0.0.1:8000/admin/login.html")
        page.fill("#username-input", "admin")
        page.fill("#password-input", "admin123")
        page.click("#login-submit-btn")
        page.wait_for_timeout(3000)

        print("2. Current URL:", page.url)
        dash_container = page.query_selector("#view-dashboard")
        is_visible = dash_container.is_visible() if dash_container else False
        inner_html = dash_container.inner_html() if dash_container else ""
        print("3. Dashboard container exists:", dash_container is not None)
        print("4. Dashboard visible:", is_visible)
        print("5. Dashboard HTML len:", len(inner_html))
        print("6. Dashboard inner HTML:\n", inner_html[:600])

        print("\n=== Console messages ===")
        for m in console_msgs:
            print("  ", m)

        print("\n=== Page errors ===")
        for e in page_errors:
            print("  ", e)

        print("\n=== Failed requests ===")
        for f in failed_requests:
            print("  ", f)

        print("\n=== API responses ===")
        for r in responses:
            if "api" in r:
                print("  ", r)

        # Now test refresh on #dashboard directly
        print("\n=== Refreshing page at #dashboard ===")
        page.goto("http://127.0.0.1:8000/admin/#dashboard")
        page.wait_for_timeout(3000)
        dash_container = page.query_selector("#view-dashboard")
        is_visible = dash_container.is_visible() if dash_container else False
        inner_html = dash_container.inner_html() if dash_container else ""
        print("Post-refresh visible:", is_visible)
        print("Post-refresh HTML len:", len(inner_html))

        # Now test navigating to #appointments and back to #dashboard
        print("\n=== Navigating to #appointments then back to #dashboard ===")
        page.click("a[data-view='appointments']")
        page.wait_for_timeout(1500)
        page.click("a[data-view='dashboard']")
        page.wait_for_timeout(1500)
        dash_container = page.query_selector("#view-dashboard")
        is_visible = dash_container.is_visible() if dash_container else False
        inner_html = dash_container.inner_html() if dash_container else ""
        print("Post-back-navigation visible:", is_visible)
        print("Post-back-navigation HTML len:", len(inner_html))

        browser.close()

if __name__ == "__main__":
    inspect_dashboard()

