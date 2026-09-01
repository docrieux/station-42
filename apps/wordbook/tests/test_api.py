from fastapi.testclient import TestClient
from wordbook.main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_api_info():
    body = client.get("/api/").json()
    assert body["service"] == "wordbook"
    assert body["message"]
