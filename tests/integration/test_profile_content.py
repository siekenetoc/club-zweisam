import base64

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.feed.models import NotificationPreference
from apps.pages.models import StaticPage

pytestmark = pytest.mark.django_db
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_profile_optional_fields_and_avatar(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(
        username="profil", email="profil@example.com", password="sehr-geheim-1234"
    )
    client.force_login(user)
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    assert "Anzeigename" in response.content.decode()
    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "profile_save",
            "username": "profil",
            "display_name": "Profilname",
            "first_name": "",
            "last_name": "",
            "pronouns": "",
            "timezone": "Europe/Berlin",
            "bio": "Ein optionaler Gedanke",
            "avatar": SimpleUploadedFile("avatar.png", PNG, content_type="image/png"),
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.display_name == "Profilname"
    assert user.bio == "Ein optionaler Gedanke"
    assert user.avatar.name.endswith(".webp")
    assert user.avatar_thumb.name.endswith(".webp")


def test_notification_preference_can_be_disabled(client):
    from apps.clubroom.models import Membership
    from apps.clubroom.services import create_clubroom

    user = User.objects.create_user(
        username="pref", email="pref@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=user, name="Pref Raum", safe_word="Anker")
    Membership.objects.filter(clubroom=clubroom, user=user).update(role="owner")
    client.force_login(user)
    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "notification_pref_save",
            "event_type": "checkin.created",
            "channel": "inapp",
            "enabled": "",
        },
    )
    assert response.status_code == 302
    pref = NotificationPreference.objects.get(user=user, clubroom=clubroom)
    assert pref.enabled is False


def test_portal_admin_can_edit_static_page(client):
    user = User.objects.create_user(
        username="contentadmin",
        email="contentadmin@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name="Plattform-Admin")
    user.groups.add(group)
    page = StaticPage.objects.get(slug="agb")
    client.force_login(user)
    assert client.get(reverse("admin_panel:content")).status_code == 200
    response = client.get(
        reverse("admin_panel:content_edit", kwargs={"kind": "page", "pk": page.pk})
    )
    assert response.status_code == 200
    assert "tinymce" in response.content.decode().lower()
    response = client.post(
        reverse("admin_panel:content_edit", kwargs={"kind": "page", "pk": page.pk}),
        {
            "title": page.title,
            "slug": page.slug,
            "content_html": "<p>Neuer Inhalt</p>",
            "is_published": "on",
        },
    )
    assert response.status_code == 302
    page.refresh_from_db()
    assert page.content_html == "<p>Neuer Inhalt</p>"
