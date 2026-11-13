import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def registration_payload(username="anna", email="anna@example.com", **overrides):
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


def test_registration_creates_verified_user(client):
    response = client.post(reverse("accounts:register"), registration_payload())
    assert response.status_code == 302
    assert response.url == reverse("clubroom:home")

    user = User.objects.get(username="anna")
    assert user.email == "anna@example.com"
    assert user.age_verified is True
    assert user.tos_accepted_at is not None


def test_registration_requires_age_and_tos(client):
    response = client.post(
        reverse("accounts:register"),
        registration_payload(age_confirmed="", tos_accepted=""),
    )
    assert response.status_code == 200
    assert User.objects.count() == 0


def test_registration_rejects_duplicate_email_case_insensitive(client):
    User.objects.create_user(
        username="existing", email="Anna@Example.com", password="sehr-geheim-1234"
    )
    response = client.post(
        reverse("accounts:register"), registration_payload(email="anna@example.com")
    )
    assert response.status_code == 200
    assert User.objects.count() == 1


def test_login_and_logout(client):
    User.objects.create_user(username="anna", email="anna@example.com", password="sehr-geheim-1234")
    response = client.post(
        reverse("accounts:login"),
        {"username": "anna", "password": "sehr-geheim-1234"},
    )
    assert response.status_code == 302
    assert response.url == reverse("clubroom:home")

    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert client.get(reverse("clubroom:home")).status_code == 200


def test_safe_word_is_encrypted_at_rest(client):
    from django.db import connection

    client.post(reverse("accounts:register"), registration_payload())
    client.post(
        reverse("clubroom:create"),
        {"name": "Unser Raum", "rules": "", "safe_word": "Anker"},
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT safe_word FROM clubroom_clubroom")
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "Anker" not in stored
