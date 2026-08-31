# apps/CLAUDE.md — building a custom app

Scope: everything under `apps/`. Root rules still apply (`../../CLAUDE.md`).
Full rationale for the dual-UI model: `docs/dual-ui.md`.

## Scaffold, don't hand-roll

```bash
just new-app notes        # name must match ^[a-z][a-z0-9_]*$
```

Copies `_template/`, substitutes the name (`appname` → `notes`, `APPNAME_` →
`NOTES_`), registers the uv workspace member, runs `uv sync`, prints the compose
+ Caddy snippets. The output is a **working dual-UI app** — `just test` passes on
it before you write a line. `_template/` itself is excluded from the workspace,
ruff and pytest — never edit an app by editing the template.

## The dual-UI route contract (mandatory)

Every app serves **two distinct UIs** — a desktop one and a mobile one, not one
responsive page — from **one container, one image, one subdomain**. Routing is
path-based and lives inside the FastAPI app:

| Path | Serves | Notes |
|---|---|---|
| `GET /` | `302` to `/d/` or `/m/` | choose by `is_mobile(request)`; preserve the query string; honour `?ui=d` / `?ui=m` override and remember it in a cookie |
| `GET /d/`, `/d/{path}` | desktop HTML | Jinja2 templates in `web/templates/desktop/` |
| `GET /m/`, `/m/{path}` | mobile HTML | Jinja2 templates in `web/templates/mobile/` |
| `GET /api/...` | JSON | the real logic; **both** UIs read from here |
| `GET /static/...` | shared CSS/JS/img | mounted once, not under `/d` or `/m`, so both UIs share URLs |
| `GET /healthz` | `{"status":"ok"}` | from `health_router`, unchanged |
| `/docs`, `/openapi.json` | FastAPI default | API only |

Rules:
- **No business logic in a UI module.** It goes in `api.py` (or `station_common`
  if it's cross-app). The desktop and mobile handlers are thin: fetch/compute via
  the same code the API uses, then render their own template.
- **Never add a second Caddy route** or a `m-<name>` hostname for the mobile UI —
  the split is internal.
- Bare `/` always redirects; the UIs never render at `/`. Templates use absolute
  links (`/static/...`, `/d/...`, `/m/...`).

## Directory layout

```
apps/<name>/
  pyproject.toml            deps; station-common always included
  Dockerfile                multi-stage; build context = repo root
  src/<name>/
    __init__.py
    settings.py              Settings(BaseAppSettings) + `settings` instance
    api.py                   make_api_router() -> APIRouter(prefix="/api"); the logic
    ui.py                    make_ui_router(desktop, mobile) -> /d/ + /m/ handlers
    main.py                  builds `app`, wires everything, calls configure_logging
    web/
      static/                shared assets  -> /static   (must exist, even if empty)
      templates/
        shared/              base layouts, partials (on both search paths)
        desktop/             pages for /d
        mobile/              pages for /m
  tests/
    test_api.py              /healthz + /api/...
    test_ui.py               / redirects (per-UA), /d/ + /m/ render, /static served
```

The Dockerfile already `COPY`s the whole `apps/<name>/` dir, so `web/` ships with
no Dockerfile change. `hello/` is a full worked example of everything below.

## main.py pattern

```python
from __future__ import annotations

from fastapi import FastAPI

from notes.api import make_api_router
from notes.settings import settings
from notes.ui import make_ui_router
from station_common import configure_logging, health_router
from station_common.web import mount_dual_ui

configure_logging(settings.log_level)

app = FastAPI(title="notes")
app.include_router(health_router)  # /healthz
app.include_router(make_api_router())  # /api/...

desktop, mobile = mount_dual_ui(app, "notes")  # registers / redirect + /static
app.include_router(make_ui_router(desktop, mobile))  # /d/ and /m/
```

- **`settings.py`** owns `Settings` (subclass `BaseAppSettings`, set
  `model_config | {"env_prefix": "NOTES_"}`). `api.py` and `ui.py` import
  `settings` from there — never from `main`, to keep imports acyclic.
- **`mount_dual_ui(app, "<pkg>")`** does device detection, the `/` → `/d/`|`/m/`
  redirect (with `?ui=` + cookie override), the `/static` mount, and returns the
  two `Jinja2Templates` envs. It does **not** add `/d/` or `/m/` — those are your
  app's routes (`ui.py`), because they render your data.
- **`ui.py` handlers stay thin:** call the same function `api.py` calls
  (`hello_info()` in the example), pass the result to
  `templates.TemplateResponse(request, "index.html", {...})`.
- `mount_dual_ui` / `is_mobile` live in
  `packages/station_common/src/station_common/web.py`. Extend them there — never
  reimplement device detection or the redirect per app.
- `just new-app <name>` already scaffolds all of the above (`hello` is the same
  shape). Fill in `api.py` + `web/templates/{desktop,mobile}/`.

## Config

- Common knobs (`LOG_LEVEL`, `TZ`) come unprefixed from the environment compose
  passes in — already handled by `BaseAppSettings`.
- App knobs use the `NOTES_` env prefix. Add a new **required** var to
  `compose.yaml` as `${VAR:?...}` and to `.env.example`.
- Reference: `packages/station_common/src/station_common/config.py`.

## Tests (required, run by `just test` + CI)

- `test_api.py`: exercise `/api/...` with `TestClient`.
- `test_ui.py`: at minimum —
  ```python
  assert client.get("/", follow_redirects=False).status_code == 302
  assert client.get("/d/").status_code == 200
  assert client.get("/m/").status_code == 200
  assert client.get("/healthz").json() == {"status": "ok"}
  ```
- Use a desktop UA and a mobile UA (`headers={"user-agent": ...}`) to assert `/`
  lands on the right one.

## Dockerfile rules

- `# syntax=docker/dockerfile:1`, multi-stage, build context **repo root**.
- `COPY pyproject.toml uv.lock ./` then `packages/` then `apps/<name>/` (cache
  order matters).
- `uv sync --frozen --no-dev --package <name>` with a cache mount.
- Runtime stage: non-root `uid 10001`, `EXPOSE 8000`, `HEALTHCHECK` on `/healthz`,
  `CMD ["uvicorn", "<name>.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

## Don't

- Don't add a Node/JS build step or an SPA framework unless a task truly needs it
  — server-rendered Jinja2 keeps builds ARM-friendly and dependency-free. If you
  must, discuss first.
- Don't publish host ports from an app service — Caddy is the only ingress.
- Don't duplicate logic between `/d/` and `/m/` handlers.
- Don't edit `_template/` to change one app.
