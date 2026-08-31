# apps/

Custom Python services you write. One directory per app. Each app is a
[uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) member and builds
into its own container image.

## Add an app

```bash
just new-app notes
```

This copies `_template/`, substitutes the name, registers the workspace member,
and prints the compose + Caddy snippets to paste in.

> **Standards:** [`apps/CLAUDE.md`](CLAUDE.md) is the contract for building an app
> — the dual-UI route split (`/` `/d/` `/m/` `/api/`), layout, tests, Dockerfile
> rules. Rationale: [`docs/dual-ui.md`](../docs/dual-ui.md).

## Anatomy of an app

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies. `station-common` is always included. |
| `src/<name>/settings.py` | `Settings(BaseAppSettings)` + a `settings` instance. `api.py`/`ui.py` import it from here. |
| `src/<name>/api.py` | `make_api_router()` → `APIRouter(prefix="/api")`, plus the shared logic function. |
| `src/<name>/ui.py` | `make_ui_router(desktop, mobile)` → the `/d/` and `/m/` handlers. |
| `src/<name>/main.py` | FastAPI `app`: `configure_logging`, `health_router`, the API router, `mount_dual_ui`, the UI router. |
| `src/<name>/web/` | `static/` (→ `/static`) + `templates/{shared,desktop,mobile}/`. |
| `tests/test_api.py`, `tests/test_ui.py` | `pytest` + `TestClient`. Run with `just test`. |
| `Dockerfile` | Multi-stage build. **Build context is the repo root.** |

## Local dev loop (no container)

```bash
uv run uvicorn notes.main:app --reload
# http://127.0.0.1:8000  and  /healthz  and  /docs
```

## Config

App-specific settings use an env prefix (`NOTES_FOO` -> `Settings.foo`). Common
knobs (`LOG_LEVEL`, `TZ`) are read without a prefix from the environment that
compose passes in. See `packages/station_common/src/station_common/config.py`.

## `_template/` is not built

It is excluded from the uv workspace, ruff, and pytest on purpose — it contains
the literal placeholder package `appname`.
