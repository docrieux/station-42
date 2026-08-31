# Station 42

Monorepo for the self-hosted tools running on my Raspberry Pi 4B (8 GB, ARM64).
Custom Python apps and off-the-shelf services, deployed with Docker Compose,
reachable from anywhere over Tailscale with real HTTPS — all on free tiers.

## How it fits together

```
        your laptop / phone (Tailscale app)
                     │  https://<tool>.<you>.duckdns.org
                     ▼
        ┌─────────────────────────────┐
        │  Raspberry Pi (Tailscale)   │
        │                             │
        │   Caddy  :80/:443           │   wildcard Let's Encrypt cert
        │     ├── pihole:8080         │   via DuckDNS DNS-01
        │     ├── hello:8000          │
        │     └── <your apps>         │
        │                             │
        │   docker network: edge      │
        └─────────────────────────────┘
```

| Layer | Tool | Cost |
|-------|------|------|
| Reach it from anywhere | Tailscale (personal) | free |
| Domain name | DuckDNS (`*.you.duckdns.org`) | free |
| HTTPS certificates | Caddy + Let's Encrypt (DNS-01) | free |
| Orchestration | Docker Compose | free |
| App runtime | Python 3.12 · FastAPI · uv workspace | free |

Details: [`docs/architecture.md`](docs/architecture.md).

## Layout

```
compose.yaml            single source of truth for the running stack
apps/                   custom Python services (uv workspace members)
  _template/            copied by `just new-app`
  hello/                worked example
packages/station_common shared settings / logging / health / dual-UI helpers
services/               notes + data for off-the-shelf images (pihole, ...)
infra/
  caddy/                reverse proxy image + Caddyfile
  tailscale/            host VPN setup notes
  scripts/              bootstrap-pi · deploy · backup · new-app
docs/                   architecture · adding a tool · remote access · operations · dual UI
```

## Quick start

### Tools

- **[uv](https://docs.astral.sh/uv/)** — required. `curl -LsSf https://astral.sh/uv/install.sh | sh`
  (or `winget install astral-sh.uv`). Manages Python and the workspace.
- **[just](https://github.com/casey/just)** — optional, just a task runner for the
  recipes below. `winget install Casey.Just` / `scoop install just` /
  `brew install just` / `cargo install just`. Without it, run the command each
  recipe wraps (shown by `just --dump`, or read the `justfile`).

### On your dev machine

```bash
uv sync --all-packages   # create the workspace venv        (no just: same command)
just test                # run all app + package tests       (no just: uv run --all-packages pytest)
just lint                # ruff check + format check         (no just: uv run --all-packages ruff check . && uv run --all-packages ruff format --check .)
just check               # validate compose.yaml             (no just: docker compose --env-file .env.example config -q)
```

Develop one app with live reload, no container:

```bash
uv run uvicorn hello.main:app --reload
```

### Day to day

```bash
just up            # build + (re)start everything
just ps            # status
just logs caddy    # follow one service
just deploy        # on the Pi: git pull + roll forward
just backup        # on the Pi: snapshot volumes to ./backups/
just new-app notes # scaffold a new app
```

## Adding tools

- **Custom app:** `just new-app <name>`, then paste the two printed snippets.
- **Off-the-shelf service:** add a block to `compose.yaml` + a route to the
  Caddyfile.

Step by step: [`docs/adding-a-tool.md`](docs/adding-a-tool.md).

## Conventions & standards

Working rules for this repo live in `CLAUDE.md` files, one per area
([root](CLAUDE.md), [`apps/`](apps/CLAUDE.md),
[`packages/station_common/`](packages/station_common/CLAUDE.md),
[`infra/caddy/`](infra/caddy/CLAUDE.md), [`services/`](services/CLAUDE.md),
[`infra/scripts/`](infra/scripts/CLAUDE.md)). Read the root one before making
changes. Every custom app ships a **separate desktop and mobile UI** — see
[`docs/dual-ui.md`](docs/dual-ui.md).

## Setting up the Pi from scratch

Assumes a Raspberry Pi 4B, an SD card (or USB SSD), and **nothing installed or
configured**. After the first boot, everything is done over SSH. Commands prefixed
`you@pc$` run on your computer; `pi$` run on the Pi.

Replace `user` with the username you choose and `user-pi` with your DuckDNS
name throughout.

### 1. Flash the OS

Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your
computer and flash the card:

- **OS:** *Raspberry Pi OS (64-bit)* — the Lite variant (no desktop) is plenty.
  64-bit is **required** for the ARM64 container images.
- Before writing, open **Edit Settings** (gear icon) and set:
  - **Hostname:** `station42`
  - **Enable SSH → Allow public-key authentication only**, and paste your public
    key. Generate one first if needed:
    ```
    you@pc$ ssh-keygen -t ed25519          # then paste ~/.ssh/id_ed25519.pub
    ```
  - **Username:** `user` (+ a password as fallback).
  - **Wireless LAN:** your Wi-Fi SSID, password and country — or leave blank and
    use Ethernet (steadier for a server).
  - **Locale:** your timezone / keyboard.

Write the card, put it in the Pi, connect power. Wait ~90 s on first boot.

### 2. SSH in

```
you@pc$ ssh user@station42.local        # mDNS — works on most home networks
# if .local doesn't resolve, get the IP from your router and use that:
# you@pc$ ssh user@192.168.1.42
```

Accept the host key. You're on the Pi.

### 3. Update the OS, install git

```
pi$ sudo apt update && sudo apt full-upgrade -y
pi$ sudo apt install -y git
pi$ sudo reboot                            # if firmware/kernel updated
```

Reconnect after the reboot.

### 4. Reserve a fixed LAN address

In your router's admin page, give the Pi a **static DHCP lease** (reserve its
current IP by MAC address). Pi-hole needs a stable address later.

### 5. Put this repo on the Pi

**Option A — clone from a Git remote (recommended).** Push the repo somewhere
first, from your computer:

```
you@pc$ cd station-42
you@pc$ git remote add origin git@github.com:<you>/station-42.git
you@pc$ git push -u origin main
```

Then on the Pi:

```
pi$ git clone https://github.com/<you>/station-42.git
pi$ cd station-42
```

For a **private** repo: generate a key on the Pi (`ssh-keygen -t ed25519`), add
`~/.ssh/id_ed25519.pub` to the repo as a **deploy key**, and clone the
`git@github.com:…` URL instead.

**Option B — copy directly, no remote.** From your computer:

```
you@pc$ rsync -av --exclude .venv --exclude .git \
        ./station-42/ user@station42.local:~/station-42/
```

(You give up `git pull`-based deploys; Option A is better long-term.)

### 6. Register a free domain (DuckDNS)

In a browser: <https://www.duckdns.org> → sign in → type a subdomain
(e.g. `user-pi`) → **add domain**. Copy the **token** shown at the top. You now
own `user-pi.duckdns.org` and all `*.user-pi.duckdns.org`.

### 7. Run the bootstrap script

```
pi$ cd ~/station-42
pi$ ./infra/scripts/bootstrap-pi.sh
```

It does four things:

1. **Installs Docker** (via `get.docker.com`) and adds `user` to the `docker`
   group.
2. **Installs Tailscale** and runs `sudo tailscale up --ssh --hostname=station42`.
   It prints a login URL — open it and approve the machine on your Tailscale
   account (make a free one if needed; the *Personal* plan is enough).
3. Copies `.env.example` to **`.env`** and opens it in an editor. Fill in:
   ```
   TZ=America/Santiago
   DUCKDNS_DOMAIN=user-pi.duckdns.org
   DUCKDNS_TOKEN=<token from step 6>
   ACME_EMAIL=you@example.com
   PIHOLE_PASSWORD=<pick a strong one>
   ```
4. Starts the stack **if** the `docker` group is active yet. If it tells you to
   re-login, do:
   ```
   pi$ newgrp docker            # or: log out and back in
   pi$ docker compose up -d --build
   ```

At the end it prints the Pi's **Tailscale IP** — `100.x.y.z`. Copy it.

> `just` is optional on the Pi. `./infra/scripts/deploy.sh`, `./infra/scripts/backup.sh`
> and plain `docker compose …` cover everything. Install the shortcut with
> `sudo apt install -y just` if you want it.

### 8. Point the domain at the Pi

On the DuckDNS dashboard, set your domain's IP to that `100.x.y.z` Tailscale
address and click **update ip**.

> **Why a private `100.x` address:** the name resolves for everyone, but that
> address is only routable *inside your tailnet* — so the tools are reachable from
> your devices on any network and invisible to everyone else. No router ports are
> opened; nothing touches the public internet.

### 9. Put your other devices on the tailnet

Install Tailscale on each laptop/phone and sign in with the **same account**:

- Windows / macOS / Linux: <https://tailscale.com/download>
- iOS / Android: App Store / Play Store

That's the only per-device step.

### 10. Verify

From a device on Tailscale (try a phone on cellular — proves "from anywhere"):

```
https://hello.user-pi.duckdns.org      → the hello page (raw JSON at /api/) + valid padlock
https://pihole.user-pi.duckdns.org     → Pi-hole admin login
```

If something's off, watch cert issuance on the Pi:

```
pi$ ./infra/scripts/deploy.sh   # or: just deploy
pi$ docker compose logs -f caddy    # look for: certificate obtained successfully
```

Now turn Tailscale **off** on the phone — the URLs stop working. That's correct.

> **Let's Encrypt rate limits:** while testing, uncomment the `acme_ca …staging…`
> line in `infra/caddy/Caddyfile`, re-run `docker compose up -d --build`, confirm a
> (browser-untrusted) staging cert shows up, then re-comment it and run again for
> the real cert.

### 11. (Optional) Make Pi-hole your network's DNS

Pi-hole only filters devices that use it for DNS. In your router's DHCP settings,
set the **DNS server** to the Pi's static LAN IP from step 4. See
[`services/pihole/README.md`](services/pihole/README.md).

### 12. (Optional) Hardening

- Tailscale admin console → machine `station42` → **Disable key expiry** so the Pi
  never falls off the tailnet.
- Tailscale SSH is on, so `ssh user@station42` now works from any tailnet device
  with no key juggling.
- `sudo apt install -y unattended-upgrades` for automatic OS security patches.

### Updating later

```
you@pc$ git push                          # after committing changes
pi$ ssh user@station42
pi$ cd station-42 && ./infra/scripts/deploy.sh     # pull + rebuild + restart
```

Troubleshooting table: [`docs/remote-access.md`](docs/remote-access.md).
