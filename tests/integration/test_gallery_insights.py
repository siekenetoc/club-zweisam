import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.gallery.models import Album, GalleryImage
from apps.insights.models import Insight, InsightVote

pytestmark = pytest.mark.django_db
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def make_room():
    anna = User.objects.create_user(
        username="anna", email="anna@example.com", password="sehr-geheim-1234"
    )
    bea = User.objects.create_user(
        username="bea", email="bea@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=anna, name="Unser Raum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=bea, role=OWNER)
    return clubroom, anna, bea


def test_gallery_upload_and_protected_image(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    clubroom, anna, _ = make_room()
    album = Album.objects.create(clubroom=clubroom, title="Erinnerungen", created_by=anna)
    client.force_login(anna)
    response = client.post(
        reverse("gallery:index"),
        {
            "action": "image",
            "album": album.pk,
            "caption": "Unser Tag",
            "image": SimpleUploadedFile("x.png", PNG, content_type="image/png"),
        },
    )
    assert response.status_code == 302
    image = GalleryImage.objects.get(album=album)
    assert image.image.name.endswith(".webp")
    assert image.thumb.name.endswith(".webp")
    response = client.get(reverse("gallery:image", kwargs={"pk": image.pk}))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/webp"

    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("gallery:image", kwargs={"pk": image.pk})).status_code == 403


def test_insights_private_share_and_vote(client):
    clubroom, anna, bea = make_room()
    client.force_login(anna)
    response = client.post(
        reverse("insights:index"), {"title": "Muster", "body": "Geheimer Gedanke"}
    )
    assert response.status_code == 302
    insight = Insight.objects.get()
    assert insight.status == "private"
    client.force_login(bea)
    assert "Geheimer Gedanke" not in client.get(reverse("insights:index")).content.decode()

    client.force_login(anna)
    client.post(reverse("insights:share", kwargs={"pk": insight.pk}))
    client.force_login(bea)
    assert "Geheimer Gedanke" in client.get(reverse("insights:index")).content.decode()
    client.post(reverse("insights:vote", kwargs={"pk": insight.pk}), {"value": "agree"})
    assert InsightVote.objects.get(insight=insight, user=bea).value == "agree"
