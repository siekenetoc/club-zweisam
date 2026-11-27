import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom

pytestmark = pytest.mark.django_db


def test_daily_answers_reveal_only_after_both(client):
    anna = User.objects.create_user(
        username="anna", email="anna@example.com", password="sehr-geheim-1234"
    )
    bea = User.objects.create_user(
        username="bea", email="bea@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=anna, name="Momente", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=bea, role=OWNER)
    client.force_login(anna)
    client.post(reverse("moments:answer"), {"answer": "Heute"})
    content = client.get(reverse("moments:index")).content.decode()
    assert "Heute" in content
    assert "bleibt verborgen" in content
    client.force_login(bea)
    client.post(reverse("moments:answer"), {"answer": "Immer"})
    content = client.get(reverse("moments:index")).content.decode()
    assert "Heute" in content and "Immer" in content
