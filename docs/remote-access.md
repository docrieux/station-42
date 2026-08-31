# Remote access — full setup

Goal: open `https://<tool>.<you>.duckdns.org` from any network, with a valid
padlock, and nothing exposed to strangers. One-time setup, then it just works.

## 1. DuckDNS (free domain)

1. Go to <https://www.duckdns.org> and sign in (GitHub/Google/etc).
2. Type a subdomain name and click **add domain**. You now own
   `yourname.duckdns.org` and every `*.yourname.duckdns.org`.
3. Copy the **token** shown at the top of the page.
4. Put both in `.env`:
   ```
   DUCKDNS_DOMAIN=yourname.duckdns.org
   DUCKDNS_TOKEN=<that token>
   ACME_EMAIL=you@example.com
   ```

## 2. Tailscale on the Pi (free VPN)

`./infra/scripts/bootstrap-pi.sh` does this, or manually:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=station42
tailscale ip -4          # note the 100.x.y.z address
```

In the Tailscale admin console, open the `station42` machine and **disable key
expiry** so it never drops off the tailnet.

## 3. Point the domain at the Pi's Tailscale IP

On the DuckDNS dashboard, set the IP for your domain to the `100.x.y.z` from the
previous step and click **update ip**. (You can also script this, but the Tailscale
IP is stable so once is enough.)

Why a `100.x` address: it resolves for everyone but is only *reachable* from
inside your tailnet. That is what keeps the tools private.

## 4. Tailscale on your other devices

Install the app and sign in with the **same account**:

- Windows / macOS: <https://tailscale.com/download>
- iOS / Android: App Store / Play Store

That's the whole per-device setup.

## 5. Start the stack and verify

```bash
just up
just logs caddy      # watch for: certificate obtained successfully
```

From a phone on cellular (proves "from anywhere"):

- `https://hello.yourname.duckdns.org` → JSON, valid padlock.
- `https://pihole.yourname.duckdns.org/admin` → Pi-hole login.
- Turn Tailscale **off** on the phone → the sites stop loading. That is correct:
  they are not on the public internet.

### First-run TLS tip

Let's Encrypt has tight rate limits. While testing, uncomment the
`acme_ca ...staging...` line in `infra/caddy/Caddyfile`, `just up`, confirm a
(untrusted) staging cert is issued, then re-comment it and `just up` again for the
real one.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Name doesn't resolve | DuckDNS IP not set, or client not on Tailscale. `nslookup yourname.duckdns.org` should return `100.x.y.z`. |
| Resolves but connection times out | Client not on the tailnet, or `tailscale status` on the Pi is down. |
| `SSL_ERROR` / self-signed | Staging CA still enabled in the Caddyfile, or cert not issued yet — `just logs caddy`. |
| Caddy log: DuckDNS API errors | Wrong `DUCKDNS_TOKEN`, or `DUCKDNS_DOMAIN` includes `https://` / a path (it must be just the host). |
| `hello` 502 in Caddy | App container not healthy — `just logs hello`, `just ps`. |

## Alternatives (documented, not set up)

- **Don't want the Tailscale app on a device?** Use Caddy's internal CA for extra
  `*.home` names and install Caddy's root cert on that device — or just use the
  Tailscale device you carry.
- **Need a genuinely public URL** for one service (e.g. a webhook receiver):
  `tailscale funnel 8000` (or per-service config) exposes it over HTTPS on your
  `*.ts.net` name without any port-forwarding. Treat anything behind Funnel as
  internet-facing and add authentication.
- **Have a real domain?** Swap the `caddy-dns/duckdns` plugin for your DNS
  provider's plugin and change `DUCKDNS_DOMAIN`; nothing else changes.
