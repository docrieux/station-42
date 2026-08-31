# Pi-hole

Network-wide ad/tracker blocking + local DNS. Runs from the `pihole/pihole:latest`
image; defined in the top-level `compose.yaml`.

## Access

- Admin UI: `https://pihole.<your>.duckdns.org/admin` (proxied by Caddy).
- Password: `PIHOLE_PASSWORD` from `.env`.
- The container serves its UI on port **8080** internally
  (`FTLCONF_webserver_port`) so it never collides with Caddy on 80/443.

## Make it your LAN's DNS (optional but the point of Pi-hole)

Pi-hole only blocks for clients that actually use it for DNS. Two ways:

1. **Router-wide (best):** set your router's DHCP DNS server to the Pi's LAN IP.
   Every device then uses Pi-hole automatically. Give the Pi a static DHCP lease.
2. **Per-device:** set the Pi's LAN IP as the DNS server manually.

Port 53 is published on the host for this. It is *not* exposed off the LAN — only
the Caddy-proxied UI is reachable over Tailscale.

## Data

Persisted at `services/pihole/data/etc-pihole/` (gitignored). Back it up with
`just backup`.

## First run

The gravity (blocklist) database downloads on first start; give it a minute.
Adjust upstream resolvers and blocklists from the admin UI under *Settings*.
