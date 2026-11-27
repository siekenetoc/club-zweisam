import os
import re
import time
import uuid
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.e2e


def confirmation_url_for(page, email):
    deadline = time.time() + 5
    while time.time() < deadline:
        response = page.request.get("http://mailhog:8025/api/v2/messages")
        if response.ok:
            for item in response.json().get("items", []):
                recipients = [
                    f"{recipient.get('Mailbox')}@{recipient.get('Domain')}"
                    for recipient in item.get("To", [])
                ]
                if email not in recipients:
                    continue
                body = item.get("Content", {}).get("Body", "")
                match = re.search(
                    r"https?://[^\s\"'<>]+/accounts/confirm-email/[^\s\"'<>]+",
                    body,
                )
                if match:
                    return match.group(0)
        time.sleep(0.2)
    raise AssertionError(f"Keine Bestätigungs-E-Mail für {email} gefunden")


def click_visible_link(page, href):
    locator = page.locator(f'a[href="{href}"]:visible')
    if locator.count():
        locator.first.click()
    else:
        page.goto(f"{os.environ.get('BASE_URL', 'https://localhost')}{href}", wait_until="load")


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
        assert "Der Raum steht" in page.get_by_role("heading", name="Der Raum steht.").inner_text()
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
        page.wait_for_url(f"{base_url}/accounts/confirm-email/")
        activation_url = confirmation_url_for(page, email)
        activation_path = urlparse(activation_url).path
        page.goto(f"{base_url}{activation_path}", wait_until="load")
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

        click_visible_link(page, "/clubraum/einladen/")
        page.wait_for_url(f"{base_url}/clubraum/einladen/")
        page.fill("#id_email", f"invite_{suffix}@example.com")
        page.select_option("#id_role", "guest")
        page.get_by_role("button", name="Einladung senden").click()
        page.wait_for_url(f"{base_url}/")
        assert "wurde versendet" in page.content()

        click_visible_link(page, "/separee/")
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
        click_visible_link(page, "/concierge/")
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
        click_visible_link(page, "/playbook/")
        page.wait_for_url(f"{base_url}/playbook/")
        page.get_by_role("button", name="Starten").first.click()
        page.wait_for_url(re.compile(r".*/playbook/lauf/\d+/"))
        assert "challengeTimer" in page.content()
        page.get_by_role("button", name="Für mich erledigt").click()
        page.wait_for_load_state("load")
        assert "Challenge gemeinsam abgeschlossen" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        click_visible_link(page, "/lounge/")
        page.wait_for_url(f"{base_url}/lounge/")
        page.locator("input[name='mood'][value='4']").check()
        page.locator("input[name='energy'][value='3']").check()
        page.locator("input[name='closeness'][value='5']").check()
        page.get_by_role("button", name="Check-in speichern").click()
        page.wait_for_load_state("load")
        content = page.content()
        assert "Check-in gespeichert" in content
        assert "Stimmung 4/5" in content
        page.fill("#shield-settings-pin", "1234")
        page.fill("#shield-settings-confirm", "1234")
        page.click("#shield-settings-save")
        page.wait_for_timeout(300)
        assert "PIN lokal gespeichert" in page.content()
        page.get_by_role("button", name="Safe Mode aktivieren").click()
        page.wait_for_load_state("load")
        assert "Safe Mode aktiv" in page.content()
        page.get_by_role("button", name="Safe Mode deaktivieren").click()
        page.wait_for_load_state("load")
        assert "Safe Mode deaktiviert" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        click_visible_link(page, "/logbuch/")
        page.wait_for_url(f"{base_url}/logbuch/")
        content = page.content()
        assert "Challenge abgeschlossen" in content
        assert "Check-in" in content

        page.goto(f"{base_url}/", wait_until="load")
        click_visible_link(page, "/punkte/")
        page.wait_for_url(f"{base_url}/punkte/")
        assert "Belohnungen" in page.content()
        page.get_by_role("button", name="Anfragen").first.click()
        page.wait_for_load_state("load")
        assert "Angefragt" in page.content()

        page.goto(f"{base_url}/", wait_until="load")
        click_visible_link(page, "/deep-talk/")
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

        click_visible_link(page, "/krisenmodus/")
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

        page.goto(f"{base_url}/", wait_until="load")
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        timing = page.evaluate("""() => {
              const overlay = document.getElementById("privacy-shield");
              const start = performance.now();
              document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
              document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
              return {
                elapsed: performance.now() - start,
                visible: !overlay.hidden,
                title: document.title,
              };
            }""")
        assert timing["visible"] is True
        assert timing["elapsed"] < 100
        assert timing["title"] == "Notizen"
        page.locator("#privacy-shield").wait_for(state="visible")
        page.wait_for_timeout(700)
        assert requests == []
        page.fill("#shield-pin-input", "1234")
        page.click("#shield-unlock-button")
        page.locator("#privacy-shield").wait_for(state="hidden")

        context.close()
        browser.close()
