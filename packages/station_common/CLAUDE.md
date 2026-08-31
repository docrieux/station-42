# packages/station_common/CLAUDE.md

The one shared library every app imports. Imported as `station_common`
(underscore); the directory is `packages/station_common/`.

## What belongs here

Only helpers that are **generic across apps** and that you'd otherwise copy-paste.
Today:

| Export | From | Purpose |
|---|---|---|
| `BaseAppSettings` | `config.py` | pydantic-settings base; common unprefixed knobs (`app_name`, `log_level`, `tz`); apps subclass and set `env_prefix` |
| `configure_logging` | `logging.py` | idempotent root logger → stdout, one line format, routes uvicorn loggers through it |
| `health_router` | `health.py` | `GET /healthz` → `{"status": "ok"}` for container + proxy probes |

Dual-UI helpers (`web.py`, imported as `from station_common.web import ...` — not
re-exported at top level, to keep `__init__` import-light):

| Export | Purpose |
|---|---|
| `is_mobile(request_or_ua)` | User-Agent regex → `bool` (a hint, not a guarantee) |
| `mount_dual_ui(app, import_name)` | mounts `/static` from `<pkg>/web/static`, registers the `/` → `/d/`\|`/m/` redirect (`?ui=` + `ui` cookie override), and **returns** `(desktop, mobile)` `Jinja2Templates`. Does **not** add `/d/` or `/m/` — the app does, since those render app data. |
| `UI_COOKIE` | name of the override cookie (`"ui"`) |

## Dependency policy

Anything added to `pyproject.toml` here is forced onto **every app and every
container image**. Keep it minimal. Current deps: `fastapi`, `pydantic-settings`,
`jinja2` (the last for `web.py` — every app needs it). Do not add anything heavier
without discussing it.

## Adding a helper

1. New function/class in a focused module (`config.py`, `logging.py`, `health.py`,
   `web.py`, …). Keep modules single-purpose.
2. Re-export it from `src/station_common/__init__.py` and list it in `__all__`.
3. Add a test to `tests/test_common.py`. `just test` and CI must stay green.
4. If it changes an app-facing contract, update `apps/CLAUDE.md`.

## Don't

- Don't put app-specific logic here.
- Don't import from `apps/` — dependency direction is apps → `station_common`, never back.
- Don't break `BaseAppSettings.model_config` merging (`model_config | {...}`); apps rely on it.
