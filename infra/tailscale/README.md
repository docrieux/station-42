# Tailscale

Tailscale is the free, zero-config VPN that makes every tool reachable "from
anywhere with wifi" without opening a single port on your router.

It runs on the **Pi host** (not in a container) so it can also provide SSH and
route traffic for the whole box. `infra/scripts/bootstrap-pi.sh` installs it.

## Pi

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=station42
tailscale ip -4          # -> 100.x.y.z  (put this in DuckDNS)
```

`--ssh` lets you `ssh station42` from any of your tailnet devices with no key
management. Consider disabling key expiry for the Pi in the admin console
(Machines -> station42 -> Disable key expiry) so it never drops off.

## Client devices

Install the Tailscale app on each laptop/phone and sign in with the **same
account**. That is the only per-device step. After that,
`https://<tool>.<your>.duckdns.org` works identically on every network.

## Why it's secure by default

The DuckDNS record points at the Pi's `100.x.y.z` Tailscale address. That range is
only routable inside your tailnet, so:

- On the tailnet  -> name resolves, Caddy answers, valid HTTPS.
- Off the tailnet -> name resolves but the address goes nowhere. Nothing is
  exposed to the public internet.

## Optional hardening / extras

- **ACLs** (admin console -> Access controls): restrict which devices may reach
  the Pi, or which ports.
- **MagicDNS**: reach the box as `station42` / `station42.<tailnet>.ts.net`
  without DuckDNS at all (no custom cert on those names though).
- **Tailscale Funnel**: if you ever need a truly public URL for one service,
  `tailscale funnel` exposes it over HTTPS without port-forwarding. See
  `docs/remote-access.md`.
- **Subnet router**: `sudo tailscale up --advertise-routes=192.168.1.0/24` to
  reach other LAN devices (e.g. the router) through the Pi.
