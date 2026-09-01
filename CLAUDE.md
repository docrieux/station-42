# CLAUDE.md — Station 42 working standards

Read this first. It is the map and the rulebook. Sub-directories have their own
`CLAUDE.md` with the detail for that area; this file links to them. If something
here and a sub-directory file disagree, the sub-directory file wins for its area.

## What this repo is

A monorepo for the self-hosted tools running on **one Raspberry Pi 4B (8 GB,
ARM64)**. Custom Python apps + off-the-shelf Docker images, orchestrated with a
single `compose.yaml`, fronted by Caddy with a real wildcard HTTPS cert, reachable
from anywhere over Tailscale. Architecture rationale: `docs/architecture.md`.

## Hard constraints — do not violate without asking

- **Free.** No paid domain, VPS, tunnel, or SaaS tier. Every piece runs on a free
  plan or on the Pi itself.
- **ARM64 / Pi 4B.** Images must build for `linux/arm64`. Assume 8 GB RAM shared
  by the whole stack; don't add heavy runtimes casually.
- **LF line endings, always.** Enforced by `.gitattributes`. Shell scripts, the
  `justfile`, Dockerfiles and the `Caddyfile` break on the Pi with CRLF.
- **Secrets never get committed.** Real values live only in `.env` (gitignored).
  `.env.example` holds placeholders. Compose reads required vars as
  `${VAR:?message}`.
- **`compose.yaml` is the single source of truth** for what runs. No hand-started
  containers.

## Fixed stack — swap only after discussion

| Layer | Choice |
|---|---|
| Reach from anywhere | Tailscale (personal tier), on the Pi host, not in a container |
| Domain | DuckDNS free subdomain, `*.<name>.duckdns.org` |
| TLS | Caddy + Let's Encrypt **DNS-01** via `caddy-dns/duckdns` (wildcard cert) |
| Ingress / routing | Caddy reverse proxy, sole owner of host ports 80/443 |
| Orchestration | Docker Compose (`name: station42`, one network `edge` = `station42_edge`) |
| App runtime | Python 3.12 · FastAPI · uvicorn · `uv` workspace · shared `station_common` |
| Task runner | `just` (optional wrapper; every recipe is a plain command) |

## Repo map

```
compose.yaml              the running stack — source of truth
compose.local.yaml        dev-only overlay for testing on this PC — never deployed
justfile                  task shortcuts (see table below)
.env / .env.example       config; .env is gitignored
apps/                     custom Python services — uv workspace members
  _template/              copied by `just new-app`; excluded from workspace/ruff/pytest
  hello/                  reference app
  CLAUDE.md               <- app-building contract (dual-UI, layout, tests)
packages/station_common/  shared settings + logging + health (+ web helpers)
  CLAUDE.md               <- what may live here, dependency policy
services/                 off-the-shelf images: notes + data only, no code
  CLAUDE.md               <- third-party service rules
infra/caddy/              proxy image (xcaddy + duckdns plugin) + Caddyfile
  Caddyfile.local         routing for `just up-local` (internal CA, *.localhost)
  CLAUDE.md               <- routing rules, cert limits
infra/tailscale/          host VPN setup notes (no code)
infra/scripts/            bootstrap-pi · deploy · backup · new-app
  CLAUDE.md               <- script conventions + exec-bit gotcha
docs/                     architecture · adding-a-tool · operations · remote-access · dual-ui · local-testing
```

## Commands (`just <recipe>` — or run the wrapped command)

| Recipe | Does |
|---|---|
| `just up` | `docker compose up -d --build` — build + (re)start everything |
| `just down` | stop + remove the stack (named volumes / bind mounts kept) |
| `just restart <svc>` | restart one service |
| `just logs <svc>` | follow one service's logs |
| `just ps` | container + health status |
| `just pull` | pull newer third-party images |
| `just check` | validate merged compose config (uses `.env`, else `.env.example`) |
| `just up-local` | **this PC:** build + run the whole stack locally — 127.0.0.1 ports + Caddy on an internal CA. Also `down-local` / `ps-local` / `logs-local`. See `docs/local-testing.md` |
| `just deploy` | **on the Pi:** `git reset --hard origin/main` + pull + `up --build` + prune |
| `just backup` | **on the Pi:** tar every `**/data/` + `.env` to `backups/` (keeps 14) |
| `just sync` | `uv sync --all-packages` — workspace venv |
| `just test` | `uv run --all-packages pytest` |
| `just lint` | `ruff check .` + `ruff format --check .` |
| `just fmt` | `ruff format .` + `ruff check --fix .` |
| `just new-app <name>` | scaffold `apps/<name>/` from `_template`, wire the workspace |

## Standard procedures

### Add a custom Python app
1. `just new-app <name>` (name = `^[a-z][a-z0-9_]*$`).
2. Build it following **`apps/CLAUDE.md`** — the dual-UI route contract is
   mandatory (`/` redirects by device, `/d/` desktop, `/m/` mobile, `/api/` JSON,
   `/healthz` unchanged).
3. Paste the printed **service block** into `compose.yaml` under `services:`.
4. Paste the printed **route** into `infra/caddy/Caddyfile`, above
   `# ---- add new apps above this line ----`.
5. Add a `127.0.0.1` port stanza to `compose.local.yaml` and mirror the route
   into `infra/caddy/Caddyfile.local`; `just up-local` and check it in a browser.
   See `docs/local-testing.md`.
6. `just check && just lint && just test`.
7. Commit only when asked. The wildcard cert already covers the new subdomain.

### Add an off-the-shelf service
See **`services/CLAUDE.md`**. Short version: compose block joining `edge`, a Caddy
route, a `services/<name>/README.md`, data under `services/<name>/data/`. Never
publish 80/443. Publish another host port only for a real LAN need (Pi-hole's 53
is the sole example). Test it before pushing with a `compose.local.yaml` stanza +
`Caddyfile.local` route, then `just up-local` (`docs/local-testing.md`) — there's
no `uvicorn` loop for a third-party image.

### Change an app's code
Edit under `apps/<name>/src/`. Local loop, no container:
`uv run uvicorn <name>.main:app --reload`. Add deps in `apps/<name>/pyproject.toml`
then `uv sync` and commit `uv.lock`. Rebuild one container:
`docker compose up -d --build <name>`.

### Deploy
Dev machine: `just test && just lint && just check`, commit, push. Pi:
`cd station-42 && just deploy` (accepts a ref: `./infra/scripts/deploy.sh origin/some-branch`).

### Update third-party images
`just pull && just up`. Nothing to commit — tags float (`:latest`, `:2`).

### Restore a backup
`just down` → `tar -xzf backups/station42-<stamp>.tar.gz` from repo root → `just up`.

## Conventions everywhere

**Python.** 3.12. `from __future__ import annotations` at the top. Full type
hints. `ruff` config in root `pyproject.toml`: line length 100, target `py312`,
lint set `E,F,I,UP,B,SIM`. Format with `just fmt` before committing.

**Every app.** Subclass `BaseAppSettings` (set `env_prefix`), call
`configure_logging(settings.log_level)`, `app.include_router(health_router)`.
Import from `station_common`. Details + dual-UI wiring: `apps/CLAUDE.md`.

**Config / env.** Common knobs are **unprefixed** and set once globally:
`LOG_LEVEL`, `TZ`. App-specific knobs use the `APPNAME_` prefix
(`NOTES_GREETING` → `Settings.greeting` for the `notes` app). New required vars go
into `compose.yaml` as `${VAR:?set VAR in .env}` **and** into `.env.example`.

**Docker.** Multi-stage. **Build context is the repo root** (so the uv workspace
+ `packages/` are visible). Run as non-root (`uid 10001`). `EXPOSE 8000`.
`HEALTHCHECK` hits `/healthz`. `CMD ["uvicorn", "<name>.main:app", "--host",
"0.0.0.0", "--port", "8000"]`.

**Compose.** `image: station42/<name>:latest`, `restart: unless-stopped`, join
`networks: [edge]`, pass `LOG_LEVEL` + `TZ`. Persist state under a bind mount
`./apps/<name>/data:/data` or `./services/<name>/data:/data` — `**/data/` is
gitignored and picked up by `just backup`.

**Caddy.** One host-matched route per app: `@<name> host <name>.{$DUCKDNS_DOMAIN}`
→ `reverse_proxy <name>:8000`, placed above the marker line. The dual-UI split is
handled **inside the app**, so it needs **no** extra Caddy routes. See
`infra/caddy/CLAUDE.md`.

**Git.** LF only. Commit/push **only when the user asks**; if on `main`, branch
first. Git user is `docrieux`. Commit messages follow
[Conventional Commits](https://www.conventionalcommits.org/): a
`type(optional scope): summary` subject (`feat`, `fix`, `docs`, `refactor`,
`test`, `chore`, `build`, `ci`, …), an optional body, and `BREAKING CHANGE:` in
the footer for anything incompatible. CI (`.github/workflows/ci.yml`) runs ruff +
pytest + `compose config -q` + an arm64 build of every image (no push).

**Shell scripts.** `bash`, `set -euo pipefail`, idempotent, LF, mode `100755`.
On Windows the exec bit is lost — restore it in the index with
`git update-index --chmod=+x infra/scripts/<file>.sh`. See `infra/scripts/CLAUDE.md`.

## Known gotchas (learned the hard way)

- **Windows `core.fileMode=false`** drops the exec bit on committed scripts →
  `Permission denied` on the Pi. Fix in the git index (above), or `chmod +x` on
  the Pi as a stopgap.
- **`docker` group** membership from `bootstrap-pi.sh` doesn't apply to the
  current SSH session — re-login / `newgrp docker` / reboot before `docker`
  commands work without sudo.
- **`xcaddy build`** in `infra/caddy/Dockerfile` compiles Caddy from Go source;
  it is **slow on the Pi** and can thrash without swap. Be patient, add swap, or
  cross-build off-Pi (`buildx --platform linux/arm64` + `docker save | ssh … docker load`).
- **Router "DNS-rebind protection"** may strip answers in `100.64.0.0/10`,
  breaking DuckDNS → Tailscale resolution. Whitelist the domain on the router.
- **Let's Encrypt rate limits:** while testing certs, uncomment the
  `acme_ca …staging…` line in `infra/caddy/Caddyfile`, verify, then re-comment.

## Before you say a task is done

Run `just lint && just test && just check`. Report failures with their output.
Don't claim the stack is up unless `just ps` shows it healthy.
