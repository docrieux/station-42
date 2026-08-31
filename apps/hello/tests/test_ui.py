import pytest
from fastapi.testclient import TestClient
from hello.main import app

DESKTOP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"


@pytest.fixture
def client():
    # Fresh instance per test so the redirect cookie doesn't leak between cases.
    with TestClient(app) as c:
        yield c


def test_root_redirects_desktop_ua_to_desktop(client):
    r = client.get("/", headers={"user-agent": DESKTOP_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/d/"


def test_root_redirects_mobile_ua_to_mobile(client):
    r = client.get("/", headers={"user-agent": MOBILE_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/m/"


def test_root_query_override_wins_over_ua(client):
    r = client.get("/?ui=m&x=1", headers={"user-agent": DESKTOP_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/m/?x=1"


def test_root_remembers_choice_via_cookie(client):
    client.get("/?ui=m", headers={"user-agent": DESKTOP_UA})
    r = client.get("/", headers={"user-agent": DESKTOP_UA}, follow_redirects=False)
    assert r.headers["location"] == "/m/"


def test_desktop_page_renders(client):
    r = client.get("/d/")
    assert r.status_code == 200
    assert "mobile site" in r.text.lower()


def test_mobile_page_renders(client):
    r = client.get("/m/")
    assert r.status_code == 200
    assert "desktop site" in r.text.lower()


def test_static_asset_served(client):
    assert client.get("/static/style.css").status_code == 200
