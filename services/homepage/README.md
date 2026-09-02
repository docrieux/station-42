# Homepage

The dashboard / front door — [gethomepage.dev](https://gethomepage.dev). Service
tiles with icons, grouped into sections, each with an up/down dot and optional
per-service widget. Runs from `ghcr.io/gethomepage/homepage:latest`; defined in
the top-level `compose.yaml`.

## Access

- **The bare domain:** `https://<your>.duckdns.org/` — Caddy's apex block
  reverse-proxies straight to `homepage:3000` (no subdomain).
- Locally: `https://station42.localhost/` or `http://localhost:8082/` after
  `just up-local`.
- The container serves on port **3000** internally. No login — it's Tailscale-only.

## Host allow-list (required)

Homepage returns a blank "host validation failed" page for any request whose
`Host` header isn't listed in `HOMEPAGE_ALLOWED_HOSTS`. `compose.yaml` sets it to
`$DUCKDNS_DOMAIN`; `compose.local.yaml` overrides it with the `.localhost` names.
If you route Homepage from a different hostname, add it there.

## Config — tracked in git

Unlike other services, Homepage's config is **not** under `data/` — it lives in
version-controlled YAML at `services/homepage/config/`, bind-mounted to
`/app/config`:

| File | What |
|---|---|
| `settings.yaml` | title, theme, section layout |
| `services.yaml` | the service tiles (grouped) |
| `widgets.yaml` | header strip (resources / search / clock) |
| `bookmarks.yaml` | link groups |

`config/logs/` is written at runtime and is gitignored.

### Variable substitution

`{{HOMEPAGE_VAR_DOMAIN}}` in any config file is replaced with the
`HOMEPAGE_VAR_DOMAIN` env var (= `$DUCKDNS_DOMAIN` in prod). Widget API keys work
the same way: put `HOMEPAGE_VAR_PIHOLE_KEY=…` in `.env`, add
`HOMEPAGE_VAR_PIHOLE_KEY` to the `homepage` service's `environment:` in
`compose.yaml`, then reference `{{HOMEPAGE_VAR_PIHOLE_KEY}}` in `services.yaml`.

## Add a tile when you add a service

Edit `services.yaml`: add an entry under the right group with `href` (the public
Caddy URL, using `{{HOMEPAGE_VAR_DOMAIN}}`), an `icon`
([Dashboard Icons](https://github.com/homarr-labs/dashboard-icons) name, `mdi-…`,
or a URL), and a `siteMonitor` pointing at the in-network address
(`http://<name>:<port>/healthz` for Station 42 apps). Commit, `just deploy`.
Homepage hot-reloads config; no rebuild needed.

## Optional: auto-discovery from compose labels

Homepage can read `homepage.*` labels off running containers instead of
hand-writing `services.yaml`. It needs the Docker socket mounted
(`/var/run/docker.sock:/var/run/docker.sock:ro`) and a `config/docker.yaml`
entry. Left off here to keep "everything is a file" and avoid handing the
dashboard socket access.

## Data

None. Config is in git; there is no database and no `data/` dir, so `just backup`
skips this service (nothing runtime-only to lose).
