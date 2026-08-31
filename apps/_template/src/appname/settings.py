"""appname configuration. Environment variables use the ``APPNAME_`` prefix."""

from __future__ import annotations

from station_common import BaseAppSettings


class Settings(BaseAppSettings):
    model_config = BaseAppSettings.model_config | {"env_prefix": "APPNAME_"}

    greeting: str = "Hello from appname"


settings = Settings()
