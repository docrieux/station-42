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

## Anatomy of an app

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies. `station-common` is always included. |
| `src/<name>/main.py` | FastAPI `app`. Mounts `health_router`, calls `configure_logging`. |
| `tests/test_main.py` | `pytest` + `TestClient`. Run with `just test`. |
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
