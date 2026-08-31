"""hello — the reference Station 42 app.

Kept deliberately tiny. It exists to prove the whole chain works end to end:
uv workspace build -> container -> Caddy route -> HTTPS from a Tailscale device.
Copy it with `just new-app <name>` and build your real thing.
"""

from __future__ import annotations

import platform

from fastapi import FastAPI

from station_common import BaseAppSettings, configure_logging, health_router


class Settings(BaseAppSettings):
    model_config = BaseAppSettings.model_config | {"env_prefix": "HELLO_"}

    greeting: str = "Hello from Station 42"


settings = Settings()
configure_logging(settings.log_level)

app = FastAPI(title="hello")
app.include_router(health_router)


@app.get("/")
def index() -> dict[str, str]:
    return {
        "service": "hello",
        "message": settings.greeting,
        "host": platform.node(),
        "machine": platform.machine(),
    }
