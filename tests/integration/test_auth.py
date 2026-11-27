import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def signup_payload(username="anna", email="anna@example.com", **overrides):
    payload = {
        "username": username,
        "email": email,
        "password1": "sehr-geheim-1234",
        "password2": "sehr-geheim-1234",
        "age_confirmed": "on",
        "tos_accepted": "on",
    }
    payload.update(overrides)
    return payload


def confirmation_path(body):
    match = re.search(r"https?://[^/]+(/accounts/confirm-email/[^\s]+)", body)
    assert match is not None
    return match.group(1)


def make_verified_user(username="anna", email="anna@example.com"):
    user = User.objects.create_user(username=username, email=email, password="sehr-geheim-1234")
    EmailAddress.objects.create(user=user, email=email.lower(), verified=True, primary=True)
    return user


def test_signup_sends_activation_and_requires_verified_email(client):
    response = client.post(reverse("accounts:register"), signup_payload())
    assert response.status_code == 302
    assert response.url == "/accounts/confirm-email/"

    user = User.objects.get(username="anna")
    assert user.age_verified is True
    assert user.tos_accepted_at is not None
    email_address = EmailAddress.objects.get(user=user)
    assert email_address.verified is False
    assert len(mail.outbox) == 1
    assert "confirm-email" in mail.outbox[0].body
    assert "https://club-zweisam.localhost/accounts/confirm-email/" in mail.outbox[0].body

    login = client.post(
        reverse("accounts:login"),
        {"login": "anna", "password": "sehr-geheim-1234"},
    )
    assert login.status_code == 302
    assert login.url == "/accounts/confirm-email/"
    assert "_auth_user_id" not in client.session

    activation = client.get(confirmation_path(mail.outbox[0].body))
    assert activation.status_code == 302
    assert "_auth_user_id" in client.session
    email_address.refresh_from_db()
    assert email_address.verified is True

    client.post(reverse("accounts:logout"))
    login = client.post(
        reverse("accounts:login"),
        {"login": "anna@example.com", "password": "sehr-geheim-1234"},
    )
    assert login.status_code == 302


def test_signup_requires_age_and_tos(client):
    response = client.post(
        reverse("accounts:register"),
        signup_payload(age_confirmed="", tos_accepted=""),
    )
    assert response.status_code == 200
    assert User.objects.count() == 0
    assert len(mail.outbox) == 0


def test_signup_rejects_duplicate_email_case_insensitive(client):
    make_verified_user(username="existing", email="Anna@Example.com")
    response = client.post(
        reverse("accounts:register"),
        signup_payload(username="neu", email="anna@example.com"),
    )
    assert response.status_code == 200
    assert User.objects.count() == 1
    assert "bereits registriert" in response.content.decode()


def test_login_and_logout(client):
    make_verified_user()
    response = client.post(
        reverse("accounts:login"),
        {"login": "anna", "password": "sehr-geheim-1234"},
    )
    assert response.status_code == 302
    assert response.url == reverse("clubroom:home")

    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert client.get(reverse("clubroom:home")).status_code == 200


def test_password_reset_by_email(client):
    user = make_verified_user()

    response = client.post(reverse("account_reset_password"), {"email": "anna@example.com"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    match = re.search(r"https?://[^/]+(/accounts/password/reset/key/[^\s]+)", mail.outbox[0].body)
    assert match is not None
    reset_path = match.group(1)

    response = client.get(reset_path, follow=True)
    assert response.status_code == 200
    set_password_path = response.request["PATH_INFO"]
    response = client.post(
        set_password_path,
        {"password1": "noch-geheimer-5678", "password2": "noch-geheimer-5678"},
    )
    assert response.status_code == 302

    user.refresh_from_db()
    assert user.check_password("noch-geheimer-5678") is True
    login = client.post(
        reverse("accounts:login"),
        {"login": "anna", "password": "noch-geheimer-5678"},
    )
    assert login.status_code == 302


def test_profile_fields_are_editable(client):
    user = make_verified_user()
    client.force_login(user)
    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "profile_save",
            "username": "anna-neu",
            "first_name": "Anna",
            "last_name": "Beispiel",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.username == "anna-neu"
    assert user.first_name == "Anna"
    assert user.last_name == "Beispiel"


def test_email_management_page_is_available(client):
    user = make_verified_user()
    client.force_login(user)
    response = client.get(reverse("account_email"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "E-Mail-Adressen" in content
    assert "anna@example.com" in content


def test_password_change_page_is_available(client):
    user = make_verified_user()
    client.force_login(user)
    response = client.get(reverse("account_change_password"))
    assert response.status_code == 200
    assert "Passwort ändern" in response.content.decode()


def test_safe_word_is_encrypted_at_rest(client):
    from django.db import connection

    user = make_verified_user()
    client.force_login(user)
    client.post(
        reverse("clubroom:create"),
        {"name": "Unser Raum", "rules": "", "safe_word": "Anker"},
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT safe_word FROM clubroom_clubroom")
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "Anker" not in stored


def test_email_test_command_uses_configured_backend():
    call_command("email_test", to="smtp-check@example.com")
    assert len(mail.outbox) == 1
    assert "SMTP-Test" in mail.outbox[0].subject
