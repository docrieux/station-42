"""appname — a Station 42 service.

Replace this with your real endpoints. The pieces that every app keeps:
  * `configure_logging(...)` at startup
  * `health_router` mounted so `/healthz` works for container + proxy probes
"""

from __future__ import annotations

from fastapi import FastAPI

from station_common import BaseAppSettings, configure_logging, health_router


class Settings(BaseAppSettings):
    """appname configuration. Environment variables use the `APPNAME_` prefix."""

    model_config = BaseAppSettings.model_config | {"env_prefix": "APPNAME_"}

    greeting: str = "Hello from appname"


settings = Settings()
configure_logging(settings.log_level)

app = FastAPI(title="appname")
app.include_router(health_router)


@app.get("/")
def index() -> dict[str, str]:
    return {"service": "appname", "message": settings.greeting}
