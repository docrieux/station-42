# Architecture

## Goals

- Host a mix of **custom Python apps** and **off-the-shelf services** on one
  Raspberry Pi 4B (8 GB, ARM64).
- Reach every tool **from any network**, not just home.
- **Nice hostnames with valid HTTPS**, not `ip:port` and cert warnings.
- **Free.** No paid domain, no paid tunnel, no VPS.
- One repo, one command to deploy.

## The pieces

| Concern | Choice | Why this one |
|---|---|---|
| Connectivity from anywhere | **Tailscale** free tier | No port-forwarding, works behind CGNAT, WireGuard-encrypted. Pi + each client join one tailnet. Nothing is exposed to the public internet. |
| Domain | **DuckDNS** free subdomain | `you.duckdns.org` plus automatic `*.you.duckdns.org`. Has an HTTP API Caddy can use for ACME. |
| TLS certs | **Caddy** with **DNS-01** challenge via the `caddy-dns/duckdns` plugin | Issues a real **wildcard** Let's Encrypt cert for `*.you.duckdns.org`. DNS-01 needs no inbound reachability, so it works even though the Pi is only on the tailnet. Auto-renews. |
| Routing / entry point | **Caddy** reverse proxy | Single process on `:80`/`:443`. Host-matched routes to each container. |
| Name resolution trick | DuckDNS A record → the Pi's **Tailscale IP** (`100.x.y.z`) | Public DNS resolves the name for everyone, but `100.x.y.z` is only routable inside your tailnet. Result: identical URLs at home and away, reachable only by your devices. |
| Orchestration | **Docker Compose** | Single-Pi scale. Easy backup (bind mounts) and rollback (git + `compose up`). Huge image ecosystem for the off-the-shelf half. |
| Custom app stack | **Python 3.12 · FastAPI · uvicorn**, packaged with a **uv workspace** | Fast dependency resolution on ARM, one lockfile, shared internal `station_common` package. FastAPI gives cheap `/healthz` + `/docs`. |

## Request flow

1. On a Tailscale device you open `https://hello.you.duckdns.org`.
2. Public DNS answers with the Pi's `100.x.y.z`. Tailscale routes that to the Pi.
3. Caddy terminates TLS with the wildcard cert, matches `host hello.you.duckdns.org`,
   and `reverse_proxy hello:8000` over the `edge` Docker network.
4. The `hello` container (uvicorn) responds.

If the device is **not** on the tailnet, step 2 still resolves but `100.x.y.z`
goes nowhere — so the tools are private by construction.

## Networking model

- One user-defined bridge network, `station42_edge` (declared as `edge` in
  `compose.yaml`). Every web tool joins it; Caddy reaches them by service name.
- Only Caddy publishes host ports (`80`, `443`).
- Exception: Pi-hole also publishes `53/tcp+udp` on the host so LAN clients can
  use it for DNS. That is LAN-only; it is not routed off the box.

## What is deliberately not here (yet)

See the end of `docs/operations.md` for the upgrade path:

- Building images in CI and pulling them on the Pi (instead of building on-device).
- Automated image/dependency updates (Watchtower / Renovate).
- Tailscale ACLs.
