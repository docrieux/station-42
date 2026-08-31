#!/usr/bin/env bash
# One-time setup for a fresh Raspberry Pi OS (64-bit) install.
# Idempotent: safe to re-run. Run it from the repo root on the Pi:
#
#   ./infra/scripts/bootstrap-pi.sh
#
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# ---- Docker Engine + compose plugin -------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    log "Installing Docker"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Added $USER to the docker group — log out/in (or reboot) for it to take effect."
else
    log "Docker already installed: $(docker --version)"
fi

# ---- Tailscale ---------------------------------------------------------
if ! command -v tailscale >/dev/null 2>&1; then
    log "Installing Tailscale"
    curl -fsSL https://tailscale.com/install.sh | sh
fi

if ! tailscale status >/dev/null 2>&1; then
    log "Bringing Tailscale up (a browser login URL will be printed)"
    sudo tailscale up --ssh --hostname=station42
else
    log "Tailscale already up"
fi

ts_ip="$(tailscale ip -4 2>/dev/null | head -n1 || true)"

# ---- .env ------------------------------------------------------------
if [[ ! -f .env ]]; then
    log "Creating .env from .env.example — edit it now with real values"
    cp .env.example .env
    "${EDITOR:-nano}" .env
else
    log ".env already exists — leaving it alone"
fi

# ---- Bring the stack up --------------------------------------------
if groups "$USER" | grep -qw docker; then
    log "Starting the stack"
    docker compose up -d --build
else
    log "Skipping 'docker compose up' — re-login for docker group membership, then run: just up"
fi

cat <<EOF

================================================================================
Next steps
================================================================================
1. DuckDNS: set the IP for your domain to this Pi's Tailscale address:

       ${ts_ip:-<run: tailscale ip -4>}

   (https://www.duckdns.org -> your domain -> "current ip" -> Update)

2. Install Tailscale on every device you want to reach the tools from, and sign
   in to the same account.

3. From one of those devices open:  https://hello.<your-domain>
   You should get JSON and a valid padlock.

4. Point your router's DHCP DNS at this Pi's LAN IP to use Pi-hole network-wide
   (see services/pihole/README.md).
================================================================================
EOF
