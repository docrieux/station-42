"""Settings base class shared by every app.

Apps subclass :class:`BaseAppSettings` and add their own fields::

    class Settings(BaseAppSettings):
        greeting: str = "hello"

    settings = Settings()  # reads env vars, then a local .env file

Every app-specific variable should be prefixed in the environment, e.g.
``NOTES_GREETING`` for an app that sets ``model_config["env_prefix"] = "NOTES_"``.
The fields below are common to all apps and are read without a prefix so the
root ``.env`` / compose ``environment:`` block can set them once.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Common runtime knobs (no prefix; set globally).
    app_name: str = "station-42-app"
    log_level: str = "INFO"
    tz: str = "UTC"
