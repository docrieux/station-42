# Adding a tool

Two kinds of tool. Pick the matching section.

---

## A. A custom Python app

### 1. Scaffold

```bash
just new-app notes
```

Creates `apps/notes/` from the template, wires it into the uv workspace, runs
`uv sync`, and prints the compose + Caddy snippets.

### 2. Write it

Edit `apps/notes/src/notes/main.py`. Keep the two shared bits:

```python
from station_common import configure_logging, health_router

configure_logging(settings.log_level)
app.include_router(health_router)  # gives you /healthz
```

Add dependencies to `apps/notes/pyproject.toml`, then `uv sync`.

Dev loop, no container:

```bash
uv run uvicorn notes.main:app --reload
```

Test: add cases to `apps/notes/tests/test_main.py`, run `just test`.

### 3. Wire it into the stack

Paste the printed **service block** under `services:` in `compose.yaml`:

```yaml
  notes:
    build:
      context: .
      dockerfile: apps/notes/Dockerfile
    image: station42/notes:latest
    restart: unless-stopped
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      TZ: ${TZ:-UTC}
    networks:
      - edge
```

Paste the printed **route** into `infra/caddy/Caddyfile`, above the
`add new apps above this line` marker:

```
    @notes host notes.{$DUCKDNS_DOMAIN}
    handle @notes {
        reverse_proxy notes:8000
    }
```

If the app needs to persist files, add a bind mount:

```yaml
    volumes:
      - ./apps/notes/data:/data
```

### 4. Ship

```bash
just check          # validate compose
git add -A && git commit -m "add notes app" && git push
# on the Pi:
just deploy
```

`https://notes.<your>.duckdns.org` is live. The wildcard cert already covers it —
no cert step.

---

## B. An off-the-shelf service (Docker image)

Example: [Uptime Kuma](https://github.com/louislam/uptime-kuma).

### 1. Add a service block to `compose.yaml`

```yaml
  uptime:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    volumes:
      - ./services/uptime/data:/app/data
    networks:
      - edge
```

Rules:
- Join `edge`.
- **Do not** publish ports 80/443 — Caddy owns them. Publish a port only if LAN
  clients must hit the service directly (rare; Pi-hole's `53` is the example).
- Persist state under `services/<name>/data/` (gitignored, picked up by
  `just backup`).
- If the image's web port isn't the one Caddy expects, note it and point
  `reverse_proxy` at the right one.

### 2. Add a Caddy route

```
    @uptime host uptime.{$DUCKDNS_DOMAIN}
    handle @uptime {
        reverse_proxy uptime:3001
    }
```

### 3. Notes + ship

Add `services/uptime/README.md` with anything non-obvious (default creds, first-run
steps). Then:

```bash
just check
git add -A && git commit -m "add uptime kuma" && git push
# on the Pi:
just deploy
```

---

## Removing a tool

1. Delete its block from `compose.yaml` and its route from the `Caddyfile`.
2. For an app: `rm -rf apps/<name>`, then `uv sync`.
3. `just deploy` (the deploy script passes `--remove-orphans`).
4. Optionally delete `services/<name>/data` or `apps/<name>/data` on the Pi.
