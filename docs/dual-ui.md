# Dual UI: separate desktop and mobile front-ends

Every custom app in `apps/` ships **two distinct UIs** — one designed for desktop,
one for mobile — not a single responsive page. This doc explains the shape and
why. The enforceable rules are in `apps/CLAUDE.md`.

## Decision

**Path split inside one container.** Each app keeps its single image, single
Caddy route and single subdomain. The two UIs are two path prefixes served by the
same FastAPI process.

Rejected alternatives:

- **One responsive page** — the requirement is two purpose-built UIs, not one that
  reflows.
- **Separate subdomains** (`hello.` / `m-hello.`) — doubles Caddy routes and the
  `*.duckdns.org` wildcard cert only covers one label, so anything cleaner like
  `m.hello.<domain>` is impossible without a second cert.
- **Separate containers** — doubles image builds and deploy surface for every
  feature, on a Pi where build time already hurts (`xcaddy`).

Path split adds nothing to the deploy model: `compose.yaml` and the `Caddyfile`
look exactly as they do for a single-UI app.

## The contract

| Path | Serves |
|---|---|
| `GET /` | `302` → `/d/` or `/m/`, chosen by `is_mobile(request)`; query string preserved; `?ui=d` / `?ui=m` forces a choice and sets a cookie that later `/` visits honour |
| `GET /d/`, `/d/{path}` | desktop HTML — Jinja2 templates in `web/templates/desktop/` |
| `GET /m/`, `/m/{path}` | mobile HTML — Jinja2 templates in `web/templates/mobile/` |
| `GET /api/...` | JSON — the app's actual logic |
| `GET /static/...` | shared CSS/JS/img, one mount, shared by both UIs |
| `GET /healthz` | `{"status": "ok"}` (from `station_common.health_router`) |
| `/docs`, `/openapi.json` | FastAPI defaults, API only |

`/` never renders a UI — it always redirects, so each template set can use
absolute links (`/static/...`, `/d/...`, `/m/...`) without worrying about the
current prefix.

## Where the logic goes

`api.py` holds the behaviour and owns `/api/...`. The desktop and mobile route
handlers are thin: they call the same functions the API layer calls, then render
their own template. **No business logic in a UI module, and nothing duplicated
between the two.** Anything generic across apps goes into `station_common`.

## Device detection

`station_common.web.is_mobile(request_or_ua)` does a User-Agent regex (the usual
`Android`, `iPhone`, `iPad`, `Mobile`, `Opera Mini`, … set). It is a hint, not a
guarantee:

- An explicit `?ui=d` or `?ui=m` always wins and is remembered in a cookie.
- Once redirected, the user is on `/d/` or `/m/` and stays there — no re-sniffing
  on every request.
- Each UI should link to the other ("Desktop site" / "Mobile site") so a wrong
  guess is one tap to fix.

## Shared helper

Rather than reimplement per app, `station_common.web` provides:

```python
desktop, mobile = mount_dual_ui(app, "notes")
```

which mounts `/static` from `notes/web/static`, builds two `Jinja2Templates`
environments (`web/templates/desktop`, `web/templates/mobile`, both with
`web/templates/shared` on the search path), and registers the `/` redirect. It
**returns** the two environments; the app adds its own `/d/` and `/m/` routes
with them (they render app data, so they can't be generic). Source:
`packages/station_common/src/station_common/web.py`.

## Layout

```
apps/notes/src/notes/
  settings.py  Settings(BaseAppSettings) + `settings`
  api.py       make_api_router() + the shared logic function
  ui.py        make_ui_router(desktop, mobile) -> /d/ + /m/
  main.py      configure_logging + health_router + api + mount_dual_ui + ui
  web/
    static/    (must exist; add .gitkeep if empty)
    templates/
      shared/  base.html, partials
      desktop/
      mobile/
```

## Testing

`tests/test_ui.py` must assert: `/` returns `302`; `/d/` and `/m/` return `200`;
a mobile UA on `/` redirects to `/m/` and a desktop UA to `/d/`; `/static/...`
serves. Use a **fresh `TestClient` per test** (fixture) — the `ui` cookie
persists in a shared client and will skew redirect assertions. `tests/test_api.py`
covers `/healthz` + `/api/...`.

## The `hello` example

`hello` implements this standard in full — read it as the reference:
`apps/hello/src/hello/{settings,api,ui,main}.py` + `web/`. Its host/machine JSON
now lives at `GET /api/`; `GET /` redirects to the desktop or mobile page.
`README.md` step 10 and `docs/remote-access.md` §5 reflect the moved URL.
