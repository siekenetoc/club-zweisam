import os
import re
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

        page.get_by_role("link", name="Séparée").click()
        page.wait_for_url(f"{base_url}/separee/")
        assert "Deck A" in page.content()
        page.get_by_role("button", name="Runde starten").first.click()
        page.wait_for_url(re.compile(r".*/separee/runde/\d+/"))
        first_answer_form = page.locator("form[action*='/antwort/']").first
        first_answer_form.locator("input[value='ja']").check()
        first_answer_form.get_by_role("button", name="Antwort speichern").click()
        page.wait_for_load_state("load")
        assert "Antwort gespeichert" in page.content()
        assert "Warte auf die Antwort" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Concierge").click()
        page.wait_for_url(f"{base_url}/concierge/")
        page.get_by_role("link", name="Wunsch stellen").click()
        page.wait_for_url(f"{base_url}/concierge/neu/")
        page.select_option("#id_type", "konkret")
        page.fill("#id_category", "Alltag")
        page.select_option("#id_intensity", "1")
        page.select_option("#id_timeframe", "woche")
        page.fill("#id_title", "E2E Wunsch")
        page.fill("#id_body", "Ein Abend ohne Handy.")
        page.get_by_role("button", name="Wunsch speichern").click()
        page.wait_for_url(re.compile(r".*/concierge/\d+/"))
        content = page.content()
        assert "E2E Wunsch" in content
        assert "Gestellt" in content

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Playbook").click()
        page.wait_for_url(f"{base_url}/playbook/")
        page.get_by_role("button", name="Starten").first.click()
        page.wait_for_url(re.compile(r".*/playbook/lauf/\d+/"))
        assert "challengeTimer" in page.content()
        page.get_by_role("button", name="Für mich erledigt").click()
        page.wait_for_load_state("load")
        assert "Challenge gemeinsam abgeschlossen" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Lounge").click()
        page.wait_for_url(f"{base_url}/lounge/")
        page.locator("input[name='mood'][value='4']").check()
        page.locator("input[name='energy'][value='3']").check()
        page.locator("input[name='closeness'][value='5']").check()
        page.get_by_role("button", name="Check-in speichern").click()
        page.wait_for_load_state("load")
        content = page.content()
        assert "Check-in gespeichert" in content
        assert "Stimmung 4/5" in content
        page.get_by_role("button", name="Safe Mode aktivieren").click()
        page.wait_for_load_state("load")
        assert "Safe Mode aktiv" in page.content()
        page.get_by_role("button", name="Safe Mode deaktivieren").click()
        page.wait_for_load_state("load")
        assert "Safe Mode deaktiviert" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Logbuch").click()
        page.wait_for_url(f"{base_url}/logbuch/")
        content = page.content()
        assert "Challenge abgeschlossen" in content
        assert "Check-in" in content

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Punkte").click()
        page.wait_for_url(f"{base_url}/punkte/")
        assert "Belohnungen" in page.content()
        page.get_by_role("button", name="Anfragen").first.click()
        page.wait_for_load_state("load")
        assert "Angefragt" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        page.get_by_role("link", name="Deep Talk").click()
        page.wait_for_url(f"{base_url}/deep-talk/")
        page.get_by_role("button", name="Gespräch starten").click()
        page.wait_for_url(re.compile(r".*/deep-talk/\d+/"))
        page.get_by_role("button", name="Besprochen").first.click()
        page.wait_for_load_state("load")
        page.get_by_role("button", name="Time-out").click()
        page.wait_for_load_state("load")
        assert "Time-out aktiv" in page.content()
        page.get_by_role("button", name="Weiter im Gespräch").click()
        page.wait_for_load_state("load")
        page.get_by_role("button", name="Sitzung beenden").click()
        page.wait_for_url(f"{base_url}/deep-talk/")

        page.get_by_role("link", name="Krisenmodus").click()
        page.wait_for_url(f"{base_url}/krisenmodus/")
        content = page.content()
        assert "Notruf" in content and "112" in content
        assert "Telefonseelsorge" in content
        page.get_by_role("button", name="Krisenraum öffnen").click()
        page.wait_for_url(re.compile(r".*/krisenmodus/\d+/"))
        assert "Notruf" in page.content()
        page.get_by_role("button", name="Krisenraum schließen").click()
        page.wait_for_url(f"{base_url}/krisenmodus/")
        assert "Notruf" in page.content()

        page.goto(f"{base_url}/admin/", wait_until="load")
        content = page.content()
        assert "Zugriff protokolliert" in content
        assert "Club Zweisam · Verwaltung" in content

        page.goto(f"{base_url}/seite/agb/", wait_until="load")
        content = page.content()
        assert "Nutzungsbedingungen" in content
        assert "Platzhalter" in content
        page.goto(f"{base_url}/seite/datenschutz/", wait_until="load")
        assert "Datenschutz" in page.content()

        context.close()
        browser.close()
