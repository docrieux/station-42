from fastapi.testclient import TestClient
from appname.main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_api_info():
    body = client.get("/api/").json()
    assert body["service"] == "appname"
    assert body["message"]
