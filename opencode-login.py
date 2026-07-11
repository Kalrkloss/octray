#!/usr/bin/env python3
"""
OpenCode Login — run this once.
Opens a browser. Log in with GitHub.
Cookies are saved for automatic usage fetching.
"""

import json
from pathlib import Path

COOKIE_FILE = Path.home() / ".config/opencode-cookies.json"
WORKSPACE_URL = "https://opencode.ai/workspace/wrk_01KW7A4093QJB0A77XNPH9SCFH/go"

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Capture API responses
        api_endpoints = []

        def on_response(response):
            url = response.url
            if "opencode.ai" in url and (
                "usage" in url.lower()
                or "api/" in url
            ):
                try:
                    body = response.json()
                    api_endpoints.append({"url": url, "body": body})
                except:
                    # Might be HTML, skip
                    pass

        page.on("response", on_response)

        print("=" * 60)
        print("Browser opened.")
        print("1. Click 'Continue with GitHub'")
        print("2. Log in to GitHub")
        print("3. Wait for the Go dashboard to load")
        print("=" * 60)
        print()

        page.goto(WORKSPACE_URL)

        # Wait until we reach the workspace page (user logged in)
        page.wait_for_url("**/workspace/**", timeout=0)

        # Let the dashboard load its data
        page.wait_for_timeout(8000)

        # Save cookies
        cookies = context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"\n✓ Saved {len(cookies)} cookies to {COOKIE_FILE}")

        # Show captured API endpoints
        if api_endpoints:
            print(f"\n✓ Discovered {len(api_endpoints)} API endpoint(s):")
            for ep in api_endpoints:
                print(f"  {ep['url']}")
                body_str = json.dumps(ep['body'], indent=2)
                # Show a preview
                if len(body_str) > 500:
                    print(f"    (response: {body_str[:200]}...)")
                else:
                    print(f"    (response: {body_str})")
        else:
            print("\nNote: No usage API endpoints captured.")
            print("The usage data might be embedded in the page HTML.")
            print("I can check for alternative endpoints.")

        input("\nPress Enter to close browser...")
        browser.close()


if __name__ == "__main__":
    main()
