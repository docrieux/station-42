from fastapi.testclient import TestClient
from hello.main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_api_info():
    body = client.get("/api/").json()
    assert body["service"] == "hello"
    assert body["message"]
    assert "machine" in body
