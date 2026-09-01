"""wordbook configuration. Environment variables use the ``WORDBOOK_`` prefix."""

from __future__ import annotations

from station_common import BaseAppSettings


class Settings(BaseAppSettings):
    model_config = BaseAppSettings.model_config | {"env_prefix": "WORDBOOK_"}

    # Where the SQLite dictionary lives. ``/data`` is the bind mount in compose;
    # for a local ``uv run`` set WORDBOOK_DB_PATH to a writable path.
    db_path: str = "/data/wordbook.db"

    # Spanish source: rae-api.com (unofficial RAE). The free tier works with no
    # key (10 req/min, 100 req/day); set WORDBOOK_RAE_API_KEY to lift that.
    rae_base_url: str = "https://rae-api.com"
    rae_api_key: str = ""

    # English source: dictionaryapi.dev (Free Dictionary API), keyless.
    dictionaryapi_base_url: str = "https://api.dictionaryapi.dev"

    # Outbound HTTP: read timeout (seconds) and how many times to retry a
    # transient failure (timeout / connection error / 5xx / 429). dictionaryapi.dev
    # in particular tends to hang on words it doesn't have, so a short timeout +
    # a retry beats one long stall.
    http_timeout: float = 6.0
    http_retries: int = 1

    # How long a live lookup (hit or "not found") is cached in-process, so a
    # search followed by a bookmark is a single upstream call.
    cache_ttl: float = 300.0


settings = Settings()
