"""hello configuration. Environment variables use the ``HELLO_`` prefix."""

from __future__ import annotations

from station_common import BaseAppSettings


class Settings(BaseAppSettings):
    model_config = BaseAppSettings.model_config | {"env_prefix": "HELLO_"}

    greeting: str = "Hello from Station 42"


settings = Settings()
