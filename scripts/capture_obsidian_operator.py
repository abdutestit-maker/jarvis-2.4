from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


FIXTURES = (
    ("compact", 360, 520, "01-compact-live.png"),
    ("download", 1180, 760, "02-command-center-live.png"),
    ("verify", 1180, 760, "03-verification-live.png"),
    ("verified", 1180, 760, "04-verified-live.png"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:1420")
    parser.add_argument("--output", default="_shots/obsidian-operator")
    parser.add_argument("--browser", default=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    browser_path = Path(args.browser).resolve()
    if not browser_path.is_file():
        raise FileNotFoundError(browser_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(browser_path), headless=True)
        try:
            for fixture, width, height, filename in FIXTURES:
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.goto(f"{args.base_url}/?fixture={fixture}", wait_until="networkidle")
                page.locator("#root").screenshot(path=str(output / filename))
                print(f"{filename}: {width}x{height}")
                page.close()
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
