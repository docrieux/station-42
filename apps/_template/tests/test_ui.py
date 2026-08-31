import pytest
from fastapi.testclient import TestClient
from appname.main import app

DESKTOP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"


@pytest.fixture
def client():
    # Fresh instance per test so the redirect cookie doesn't leak between cases.
    with TestClient(app) as c:
        yield c


def test_desktop_ua_redirects_to_d(client):
    r = client.get("/", headers={"user-agent": DESKTOP_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/d/"


def test_mobile_ua_redirects_to_m(client):
    r = client.get("/", headers={"user-agent": MOBILE_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/m/"


def test_pages_render(client):
    assert client.get("/d/").status_code == 200
    assert client.get("/m/").status_code == 200


def test_static_served(client):
    assert client.get("/static/style.css").status_code == 200
