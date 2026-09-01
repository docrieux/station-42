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

    # English source: freedictionaryapi.com (Wiktionary-derived), keyless.
    freedict_base_url: str = "https://freedictionaryapi.com"

    # Outbound HTTP: read timeout (seconds) and how many times to retry a
    # transient failure (connection error / 5xx / 429). A read timeout is not
    # retried (see wordbook.sources._http).
    http_timeout: float = 6.0
    http_retries: int = 1

    # In-process cache: how long a live lookup (hit or "not found") is held so a
    # search followed by a bookmark is a single upstream call.
    cache_ttl: float = 300.0

    # Persistent cache (SQLite): successful lookups are kept **forever** — source
    # dictionaries are effectively static, so the RAE daily quota is only ever
    # spent on a word's first-ever lookup. A confirmed "not found" is trusted for
    # this many days, then re-checked (a word could get added upstream).
    lookup_cache_days: int = 30


settings = Settings()
