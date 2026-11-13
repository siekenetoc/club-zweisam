import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_home_page_renders(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Club Zweisam" in content
    assert "dist/css/main.css" in content
    assert "dist/js/main.js" in content


def test_health_endpoint(client):
    response = client.get(reverse("healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "club-zweisam"}


def test_no_external_asset_sources(client):
    content = client.get(reverse("home")).content.decode("utf-8")
    assert "http://" not in content
    assert "https://" not in content
