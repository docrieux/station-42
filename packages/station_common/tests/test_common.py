import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from station_common import BaseAppSettings, configure_logging, health_router


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
