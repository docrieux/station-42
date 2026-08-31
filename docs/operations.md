# Operations

## Deploy a change

```bash
# dev machine
just test && just lint && just check
git commit -am "..." && git push

# Pi (ssh station42)
cd station-42
just deploy            # git reset --hard origin/main, pull images, up --build, prune
```

`deploy.sh` accepts a ref: `./infra/scripts/deploy.sh origin/some-branch`.

## Update third-party images

```bash
just pull             # docker compose pull
just up               # recreate containers on the new images
```

Pi-hole, Caddy base, etc. follow floating tags (`:latest`, `:2`), so `pull` is all
it takes. Commit nothing — the tag is already in `compose.yaml`.

## Backups

```bash
just backup           # -> backups/station42-YYYYmmdd-HHMMSS.tar.gz  (keeps last 14)
```

Contents: every `**/data/` bind mount (Pi-hole config, app data, Caddy certs) plus
`.env`.

**Restore:**

```bash
just down
tar -xzf backups/station42-<stamp>.tar.gz     # from the repo root
just up
```

Copy the tarballs off the Pi periodically (`scp`, rsync to a NAS, cron to cloud
storage — your call).

## Logs & health

```bash
just ps                       # container + health status
just logs <svc>               # follow one
docker compose logs --since 1h caddy
docker stats --no-stream      # live CPU / memory
```

Every custom app answers `GET /healthz`; Caddy and Docker both probe it.

## Resource notes (Pi 4, 8 GB)

Plenty of headroom. Rough idle footprint: Caddy ~15 MB, Pi-hole ~60 MB, a FastAPI
app ~40 MB each. If you pile on heavy services (media transcoding, databases),
watch `docker stats` and set `deploy.resources.limits` in `compose.yaml`.

Use the 64-bit Raspberry Pi OS so ARM64 images work.

## Common tasks

| Task | Command |
|---|---|
| Restart one service | `just restart <svc>` |
| Rebuild one app after code change | `docker compose up -d --build <svc>` |
| Shell into a container | `docker compose exec <svc> sh` |
| Wipe + recreate a service's data | `just down` · `rm -rf services/<svc>/data` · `just up` |
| See merged compose config | `just check` then `docker compose config` |

## Upgrade path (when the repo grows)

1. **Build in CI, pull on the Pi.** Add a GHCR push to `.github/workflows/ci.yml`
   (`docker/build-push-action`, `platforms: linux/arm64`), change `compose.yaml`
   from `build:` to `image: ghcr.io/<you>/station42-<app>:<tag>`, and `deploy.sh`
   becomes just `docker compose pull && up -d`. Faster, and the Pi stops
   compiling.
2. **Auto-updates.** Add [Watchtower](https://containrrr.dev/watchtower/) for
   third-party images, or [Renovate](https://docs.renovatebot.com/) for
   `pyproject.toml` + image tags via PRs.
3. **Tailscale ACLs.** Lock down which tailnet devices can reach the Pi / which
   ports, in the admin console.
4. **Secrets.** If `.env` grows sensitive, move to
   [SOPS](https://github.com/getsops/sops) + age, or Docker secrets.
