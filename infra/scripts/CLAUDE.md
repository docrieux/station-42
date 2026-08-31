# infra/scripts/CLAUDE.md

Operational shell scripts. Run on the Pi (except during local testing).

| Script | Run when | Does |
|---|---|---|
| `bootstrap-pi.sh` | once, on a fresh Pi | installs Docker + Tailscale, `tailscale up --ssh`, creates `.env` from example, starts the stack if the `docker` group is active |
| `deploy.sh [ref]` | every deploy | `git fetch` + `reset --hard` to `ref` (default `origin/main`), `compose pull --ignore-buildable`, `up -d --build --remove-orphans`, prune |
| `backup.sh` | before risky changes / on a schedule | tars every `**/data/` + `.env` to `backups/station42-<stamp>.tar.gz`, keeps the last 14 |
| `new-app.sh <name>` | scaffolding an app | copies `apps/_template`, substitutes the name, `uv sync`, prints compose + Caddy snippets |

## Conventions for any script here

- `#!/usr/bin/env bash`, `set -euo pipefail`.
- **Idempotent** — safe to re-run. Guard every mutating step.
- Resolve the repo root the standard way and `cd` to it:
  ```bash
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd "$repo_root"
  ```
- **LF endings, executable bit set** (mode `100755`). On Windows the bit is lost
  on commit (`core.fileMode=false`); restore it in the index:
  ```bash
  git update-index --chmod=+x infra/scripts/<file>.sh
  ```
  On the Pi as a stopgap: `chmod +x infra/scripts/*.sh`.
- Prefix progress output with `==> ` (see `log()` in `bootstrap-pi.sh`).
- No secrets in the script or in output. Read config from `.env` / the environment.

## Testing

No CI coverage for these. Test a change by running it on the Pi (or a throwaway
clone). `bootstrap-pi.sh` and `backup.sh` are safe to re-run; `deploy.sh` does a
hard reset, so only run it where that's intended.
