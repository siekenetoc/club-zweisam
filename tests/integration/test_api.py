import pytest

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom

pytestmark = pytest.mark.django_db


def make_room():
    user = User.objects.create_user(
        username="api-user", email="api@example.com", password="sehr-geheim-1234"
    )
    partner = User.objects.create_user(
        username="api-partner", email="api-partner@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=user, name="API Raum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=partner, role=OWNER)
    return clubroom, user, partner


def test_api_requires_authentication(client):
    assert client.get("/api/v1/me/").status_code in {401, 403}


def test_api_profile_and_mood_for_member(client):
    clubroom, user, _ = make_room()
    client.force_login(user)
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert response.json()["username"] == "api-user"
    response = client.get("/api/v1/mood/", {"tage": 7})
    assert response.status_code == 200
    assert response.json()["days"] == 7


def test_api_blocks_staff_accounts(client):
    user = User.objects.create_user(
        username="api-staff",
        email="api-staff@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    client.force_login(user)
    assert client.get("/api/v1/me/").status_code in {302, 403}
