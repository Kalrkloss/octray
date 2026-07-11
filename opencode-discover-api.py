#!/usr/bin/env python3
"""
OpenCode API Discovery
Uses saved cookies to load the dashboard and capture API calls.
"""
import json
from pathlib import Path

COOKIE_FILE = Path.home() / ".config/opencode-cookies.json"
OUTPUT_FILE = Path.home() / ".config/opencode-api-endpoints.json"
WORKSPACE_URL = "https://opencode.ai/workspace/wrk_01KW7A4093QJB0A77XNPH9SCFH/go"

from playwright.sync_api import sync_playwright


def main():
    cookies = json.loads(COOKIE_FILE.read_text())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        api_calls = []

        def on_response(response):
            url = response.url
            if "opencode.ai" in url and response.status == 200:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "text" in content_type:
                    body_len = len(response.body())
                    # Only capture non-HTML responses that are likely API data
                    text = response.text()[:200]
                    if "<!DOCTYPE" not in text and "<html" not in text and text.strip():
                        api_calls.append({
                            "url": url,
                            "status": response.status,
                            "type": content_type,
                            "preview": text[:200],
                        })
                        print(f"  [{response.status}] {url}")
                        print(f"    -> {text[:100]}")

        page.on("response", on_response)

        print("Loading dashboard...")
        page.goto(WORKSPACE_URL, wait_until="networkidle")
        page.wait_for_timeout(5000)

        print(f"\nCaptured {len(api_calls)} potential API calls")

        if api_calls:
            OUTPUT_FILE.write_text(json.dumps(api_calls, indent=2))
            print(f"Saved to {OUTPUT_FILE}")

        # Also try to extract usage data from the page
        try:
            text = page.inner_text("main")
            print(f"\nPage text (first 2000 chars):")
            print(text[:2000])
        except:
            pass

        browser.close()


if __name__ == "__main__":
    main()
