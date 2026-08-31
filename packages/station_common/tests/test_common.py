import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from station_common import BaseAppSettings, configure_logging, health_router
from station_common.web import is_mobile


def test_health_router_returns_ok():
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    resp = client.get("/healthz")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_configure_logging_is_idempotent():
    configure_logging("DEBUG")
    configure_logging("WARNING")  # second call must not stack handlers

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.WARNING


def test_base_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = BaseAppSettings()

    assert settings.log_level == "DEBUG"


def test_is_mobile():
    assert is_mobile("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)")
    assert is_mobile("Mozilla/5.0 (Linux; Android 14) Mobile Safari/537.36")
    assert not is_mobile("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    assert not is_mobile("")
