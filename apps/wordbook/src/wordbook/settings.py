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

    # Outbound HTTP timeout (seconds) and how long a live lookup is cached
    # in-process so a search followed by a bookmark is a single upstream call.
    http_timeout: float = 10.0
    cache_ttl: float = 300.0


settings = Settings()
