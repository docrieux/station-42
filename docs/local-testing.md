# Local testing

Run the whole containerised stack on your dev machine before it ever reaches the
Pi. This exercises what `uv run uvicorn ...` can't: the image build, off-the-shelf
services, the `edge` network, and Caddy host-routing.

The production path (`compose.yaml`, `just up`, `just deploy`) is untouched by any
of this. The extra file is `compose.local.yaml`, layered on with an explicit
`-f`; because it isn't named `compose.override.yaml`, the Pi's `deploy.sh` never
picks it up.

## The loop

```bash
just up-local        # docker compose -f compose.yaml -f compose.local.yaml up -d --build
just ps-local        # status -- wait for healthy
just logs-local hello
just down-local
```

No `.env` needed — the recipes fall back to `.env.example` (same as `just
check`). The DuckDNS/ACME placeholders in it are never used locally: the local
Caddy runs its own CA.

## Reaching an app

Two ways, both live at once:

| Way | URL | Good for |
|---|---|---|
| Direct port | `http://localhost:<port>/` | `curl`, scripts, quick checks |
| Routed via Caddy | `https://<name>.station42.localhost/` | testing the real proxy + TLS path in a browser |

Browsers (Chrome, Edge, Firefox) resolve `*.localhost` to loopback on their own —
nothing to add to the hosts file. For `curl` on the routed URL:

```bash
curl -k --resolve hello.station42.localhost:443:127.0.0.1 \
  https://hello.station42.localhost/healthz
```

### Port map

Keep this in sync with the header comment in `compose.local.yaml` and the routes
in `infra/caddy/Caddyfile.local`.

| Port | Service |
|---|---|
| 8000 | reserved for `uv run uvicorn <app>.main:app --reload` (no container) |
| 8001 | hello |
| 8002 | wordbook |
| 8003+ | new apps |
| 8081 | pihole UI |
| 8082+ | new services |

## Trusting the local CA (optional)

The routed URLs serve a cert from Caddy's internal CA, so browsers warn until you
trust its root. Either click through the warning / use `curl -k`, or install the
root once:

1. `just up-local` at least once so Caddy generates it.
2. Import `infra/caddy/data-local/caddy/pki/authorities/local/root.crt` into
   Windows **Trusted Root Certification Authorities** (double-click → Install
   Certificate → Local Machine → place in that store), or via PowerShell:
   `Import-Certificate -FilePath infra\caddy\data-local\caddy\pki\authorities\local\root.crt -CertStoreLocation Cert:\LocalMachine\Root`
3. Restart the browser.

`infra/caddy/data-local/` and `config-local/` are gitignored.

## Adding a tool to the local stack

When you add an app or service (see [`adding-a-tool.md`](adding-a-tool.md)):

- **App:** add a stanza to `compose.local.yaml` publishing the next free port,
  and mirror the `@name` route into `infra/caddy/Caddyfile.local` with a
  `<name>.station42.localhost` host:

  ```yaml
    notes:
      ports:
        - "127.0.0.1:8002:8000"
  ```

- **Service:** same, using the port the image serves.

`just new-app` prints these steps.

## Architecture note

Local images build for your PC's architecture (amd64); the Pi is arm64. CI
arm64-builds every image on every push, so arch-specific breakage is still caught
before a deploy — but if you're touching native dependencies, do a real check on
the Pi.
