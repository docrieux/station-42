# services/CLAUDE.md

Off-the-shelf, third-party Docker images (Pi-hole today). **No code here** — each
sub-directory is notes + bind-mounted data for one upstream image. The service
definition itself lives in the top-level `compose.yaml`.

## Adding a service

1. **Compose block** under `services:` in `compose.yaml`:
   - `image:` a pinned or floating upstream tag.
   - `restart: unless-stopped`.
   - `networks: [edge]` so Caddy can reach it by name.
   - **Do not publish 80/443.** Publish another host port only if LAN clients must
     hit the service directly — Pi-hole's `53:53/tcp+udp` is the only current
     example, and it's LAN-only, not routed off the box.
   - Persist state with a bind mount `./services/<name>/data/...:/...` — `**/data/`
     is gitignored and captured by `just backup`.
   - Pass required config as `${VAR:?...}` and add it to `.env.example`.
2. **Caddy route** in `infra/caddy/Caddyfile` (above the marker), pointing
   `reverse_proxy` at the port the image actually serves. See `infra/caddy/CLAUDE.md`.
3. **`services/<name>/README.md`** — default credentials, first-run steps, the
   internal port, anything non-obvious.
4. `just check` then `just up` (Pi: `just deploy`).

## Dual-UI standard does not apply here

The `/` `/d/` `/m/` `/api/` contract is for **custom apps** (`apps/`). A
third-party service keeps whatever UI it ships; just reverse-proxy its port as-is.

## Removing a service

Delete its compose block + Caddy route, `just deploy` (the deploy script passes
`--remove-orphans`), then optionally `rm -rf services/<name>/data` on the Pi.
