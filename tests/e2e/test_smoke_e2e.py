import os

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.e2e


def test_home_page_over_caddy():
    base_url = os.environ.get("BASE_URL", "https://localhost")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(base_url, wait_until="load")
        assert "Club Zweisam" in page.title()
        assert "Der Raum steht" in page.locator("h1").inner_text()
        health = page.request.get(f"{base_url}/healthz")
        assert health.ok
        assert health.json()["status"] == "ok"
        context.close()
        browser.close()
