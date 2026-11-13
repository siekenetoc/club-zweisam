import os
import uuid

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.e2e


def launch_page(playwright):
    browser = playwright.chromium.launch()
    context = browser.new_context(ignore_https_errors=True)
    return browser, context, context.new_page()


def test_home_page_over_caddy():
    base_url = os.environ.get("BASE_URL", "https://localhost")
    with sync_playwright() as playwright:
        browser, context, page = launch_page(playwright)
        page.goto(base_url, wait_until="load")
        assert "Club Zweisam" in page.title()
        assert "Der Raum steht" in page.locator("h1").inner_text()
        health = page.request.get(f"{base_url}/healthz")
        assert health.ok
        assert health.json()["status"] == "ok"
        context.close()
        browser.close()


def test_registration_and_clubroom_creation():
    base_url = os.environ.get("BASE_URL", "https://localhost")
    suffix = uuid.uuid4().hex[:10]
    username = f"e2e_{suffix}"
    email = f"{username}@example.com"
    room_name = f"E2E Raum {suffix}"
    password = "sehr-geheim-1234"

    with sync_playwright() as playwright:
        browser, context, page = launch_page(playwright)
        page.goto(f"{base_url}/registrieren/", wait_until="load")
        page.fill("#id_username", username)
        page.fill("#id_email", email)
        page.fill("#id_password1", password)
        page.fill("#id_password2", password)
        page.check("#id_age_confirmed")
        page.check("#id_tos_accepted")
        page.click("button[type=submit]")
        page.wait_for_url(f"{base_url}/")
        assert "Noch kein Clubraum" in page.content()

        page.get_by_role("link", name="Clubraum gründen").click()
        page.wait_for_url(f"{base_url}/clubraum/neu/")
        page.fill("#id_name", room_name)
        page.fill("#id_safe_word", "Anker")
        page.get_by_role("button", name="Clubraum gründen").click()
        page.wait_for_url(f"{base_url}/")
        content = page.content()
        assert room_name in content
        assert "Hauptmitglied" in content

        context.close()
        browser.close()
