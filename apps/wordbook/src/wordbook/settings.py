"""wordbook configuration. Environment variables use the ``WORDBOOK_`` prefix."""

from __future__ import annotations

from station_common import BaseAppSettings


class Settings(BaseAppSettings):
    model_config = BaseAppSettings.model_config | {"env_prefix": "WORDBOOK_"}

    greeting: str = "Hello from wordbook"


settings = Settings()
