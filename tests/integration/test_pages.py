import base64
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.pages.models import PageMedia, StaticPage

pytestmark = pytest.mark.django_db

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def make_superuser():
    return User.objects.create_superuser(
        username="root", email="root@example.com", password="sehr-geheim-1234"
    )


def make_staff(username="staff", platform_admin=False):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    if platform_admin:
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name="Plattform-Admin")
        user.groups.add(group)
    return user


def test_seed_pages_exist_and_are_public(client):
    assert StaticPage.objects.count() == 5
    for slug in ("agb", "impressum", "datenschutz", "partner", "disclaimer"):
        page = StaticPage.objects.get(slug=slug)
        assert page.is_published is True
        response = client.get(reverse("pages:detail", kwargs={"slug": slug}))
        assert response.status_code == 200
        assert page.title in response.content.decode()


def test_unpublished_page_is_hidden(client):
    page = StaticPage.objects.get(slug="agb")
    page.is_published = False
    page.save(update_fields=["is_published"])
    assert client.get(reverse("pages:detail", kwargs={"slug": "agb"})).status_code == 404
    assert client.get(reverse("pages:detail", kwargs={"slug": "unbekannt"})).status_code == 404


def test_footer_links_to_pages(client):
    content = client.get(reverse("clubroom:home")).content.decode()
    for slug in ("agb", "impressum", "datenschutz", "partner", "disclaimer"):
        assert reverse("pages:detail", kwargs={"slug": slug}) in content


def test_only_platform_admins_can_edit(client):
    page = StaticPage.objects.get(slug="agb")
    change_url = reverse("admin:pages_staticpage_change", args=[page.pk])

    superuser = make_superuser()
    client.force_login(superuser)
    assert client.get(change_url).status_code == 200

    staff = make_staff("staff")
    client.force_login(staff)
    assert client.get(change_url).status_code == 403

    platform_admin = make_staff("platform", platform_admin=True)
    client.force_login(platform_admin)
    assert client.get(change_url).status_code == 200
    assert client.get(reverse("admin:pages_staticpage_add")).status_code == 200


def test_admin_uses_local_tinymce(client):
    page = StaticPage.objects.get(slug="agb")
    client.force_login(make_superuser())
    content = client.get(reverse("admin:pages_staticpage_change", args=[page.pk])).content.decode()
    assert "dist/tinymce/tinymce.min.js" in content
    assert "js/tinymce-init.js" in content
    assert "tinymce-editor" in content
    assert "cdn" not in content.lower()


def test_image_upload_through_admin(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    page = StaticPage.objects.get(slug="agb")
    client.force_login(make_superuser())
    change_url = reverse("admin:pages_staticpage_change", args=[page.pk])
    form_html = client.get(change_url).content.decode()
    match = re.search(r'name="([^"]+)-TOTAL_FORMS"', form_html)
    assert match is not None
    prefix = match.group(1)

    upload = SimpleUploadedFile("bild.png", PNG_BYTES, content_type="image/png")
    data = {
        "title": page.title,
        "slug": page.slug,
        "content_html": page.content_html,
        "is_published": "on",
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-file": upload,
        f"{prefix}-0-alt_text": "Ein Testbild",
    }
    response = client.post(change_url, data, follow=True)
    assert response.status_code == 200
    media = PageMedia.objects.get(page=page)
    assert media.alt_text == "Ein Testbild"
    assert media.file.name.startswith("pages/")

    page.refresh_from_db()
    assert page.updated_by.username == "root"
    public = client.get(reverse("pages:detail", kwargs={"slug": "agb"}))
    content = public.content.decode()
    assert "Ein Testbild" in content
    assert media.file.url in content
