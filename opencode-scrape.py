#!/usr/bin/env python3
"""
OpenCode Usage Scraper
Loads the Go dashboard with saved cookies and extracts usage percentages.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

COOKIE_FILE = Path.home() / ".config/opencode-cookies.json"
CACHE_FILE = Path.home() / ".config/opencode-usage-cache.json"
WORKSPACE_URL = "https://opencode.ai/workspace/wrk_01KW7A4093QJB0A77XNPH9SCFH/go"

from playwright.sync_api import sync_playwright


def scrape() -> dict | None:
    if not COOKIE_FILE.exists():
        return None

    cookies = json.loads(COOKIE_FILE.read_text())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        page.goto(WORKSPACE_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        text = page.inner_text("main")
        browser.close()

    # Parse German text labels
    labels_map = {
        "rolling": ["Rolling Usage", "Fortlaufende Nutzung", "Rolling Usage"],
        "weekly": ["Weekly Usage", "Wöchentliche Nutzung"],
        "monthly": ["Monthly Usage", "Monatliche Nutzung"],
    }

    lines = text.split("\n")
    result = {"percentages": {}, "resets": {}, "raw_text": text}

    for key, label_variants in labels_map.items():
        for i, line in enumerate(lines):
            if any(v in line for v in label_variants):
                # Next non-empty line should have the percentage
                for j in range(i + 1, min(i + 5, len(lines))):
                    pct_match = re.search(r"(\d+)%", lines[j])
                    if pct_match:
                        result["percentages"][key] = int(pct_match.group(1))
                        break

                # Look for reset time
                for j in range(i + 1, min(i + 8, len(lines))):
                    if "reset" in lines[j].lower() or "Resets" in lines[j] or "Setzt" in lines[j]:
                        # Extract the time string
                        time_str = lines[j].strip()
                        # Clean up common patterns
                        time_str = re.sub(r"^(Resets in|Setzt zurück in)\s*", "", time_str)
                        result["resets"][key] = time_str.strip()
                        break
                break

    result["timestamp"] = datetime.now(timezone.utc).timestamp()
    return result


def main():
    data = scrape()
    if data:
        CACHE_FILE.write_text(json.dumps(data, indent=2))
        print("Saved usage data:")
        print(f"  Rolling: {data['percentages'].get('rolling', '?')}% (reset {data['resets'].get('rolling', '?')})")
        print(f"  Weekly:  {data['percentages'].get('weekly', '?')}% (reset {data['resets'].get('weekly', '?')})")
        print(f"  Monthly: {data['percentages'].get('monthly', '?')}% (reset {data['resets'].get('monthly', '?')})")
    else:
        print("Not logged in. Run the Login with GitHub option first.")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
