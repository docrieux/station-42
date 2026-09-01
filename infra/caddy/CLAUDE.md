# infra/caddy/CLAUDE.md

Caddy is the **sole ingress**. It owns host ports 80/443, terminates TLS with a
wildcard Let's Encrypt cert, and host-matches to each container over the `edge`
network. Two files here: `Dockerfile` (Caddy + DuckDNS plugin) and `Caddyfile`
(routing).

## Adding a route (one per app/service)

Inside the `*.{$DUCKDNS_DOMAIN}` block, **above** `# ---- add new apps above this
line ----`:

```
    @notes host notes.{$DUCKDNS_DOMAIN}
    handle @notes {
        reverse_proxy notes:8000
    }
```

- Custom apps listen on `8000`. Off-the-shelf images: use the port the image
  actually serves (e.g. `reverse_proxy pihole:8080`); note it in the service README.
- If the UI lives under a sub-path (Pi-hole's `/admin`), add
  `redir / /admin/ 302` inside the `handle`.
- **Mirror the block into `Caddyfile.local`** (same `handle`, host
  `<name>.station42.localhost`) so `just up-local` can route it too. See
  `docs/local-testing.md`.

## Dual-UI apps need NO change here

The desktop/mobile split is path-based **inside the app** (`/`, `/d/`, `/m/`,
`/api/` — see `apps/CLAUDE.md`). One app = one `@name host name.{$DUCKDNS_DOMAIN}`
route → `reverse_proxy name:8000`. Do not add `m-name.` hostnames or per-UI
routes.

## Wildcard cert covers exactly one label

The cert is `*.{$DUCKDNS_DOMAIN}`. `hello.station42.duckdns.org` is covered;
`hello.m.station42.duckdns.org` (two labels) is **not**. Keep every service name
a single label under the domain.

## The `Dockerfile` is slow

`RUN xcaddy build --with github.com/caddy-dns/duckdns` compiles Caddy from Go
source. On the Pi this takes minutes and can thrash without swap. Options if it's
a problem: add BuildKit cache mounts (`/root/.cache/go-build`, `/go/pkg/mod`) and
pin `caddy:2.x-builder` / `caddy:2.x`; or cross-build off-Pi
(`docker buildx build --platform linux/arm64 …` then `docker save | ssh … docker load`).
CI already builds this image for arm64 as a smoke test.

## Cert testing

While iterating on TLS, uncomment in the global block:
`acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`, `just up`,
confirm a (browser-untrusted) staging cert is issued, then re-comment and
`just up` again for the real one. This dodges Let's Encrypt's tight rate limits.
`resolvers 1.1.1.1` in the `tls` block is required so the DNS-01 challenge can
see the DuckDNS TXT record.

## Env (from compose, from `.env`)

`DUCKDNS_DOMAIN` (bare host, no scheme/path), `DUCKDNS_TOKEN`, `ACME_EMAIL`.
Wrong token or a domain with `https://`/a path in it → DuckDNS API errors in the
Caddy log.

## Apply / persist

`just restart caddy` reloads config; `just up` rebuilds if the image or Caddyfile
changed. Certs and Caddy state persist in `infra/caddy/data/` and
`infra/caddy/config/` (both gitignored, both in `just backup`).

## Don't

- Don't publish any other service's ports through here or in compose.
- Don't move ports 80/443 off Caddy.
- Don't hand-edit issued certs under `data/`.
