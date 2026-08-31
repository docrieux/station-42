# services/

Off-the-shelf, third-party services. Unlike `apps/`, there is no code here — each
subdirectory holds notes and any config/data for one upstream image. The actual
service definition lives in the top-level `compose.yaml`.

## Add a service

1. Add a block under `services:` in `compose.yaml`. Join the `edge` network so
   Caddy can reach it. Do **not** publish ports 80/443 (Caddy owns those); publish
   only ports that must be reachable directly on the LAN (e.g. Pi-hole's port 53).
2. Add a host-matched route in `infra/caddy/Caddyfile`.
3. Put persistent data under `services/<name>/data/` (bind mount, gitignored) and
   document anything non-obvious in `services/<name>/README.md`.
4. `just up`.

Current services: **pihole**.
