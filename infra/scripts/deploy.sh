#!/usr/bin/env bash
# Roll the running stack forward to the latest commit. Run on the Pi.
#
#   ./infra/scripts/deploy.sh [git-ref]
#
# Default ref is origin/main.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

ref="${1:-origin/main}"

echo "==> Fetching"
git fetch --prune

echo "==> Checking out $ref"
git checkout --quiet "${ref#origin/}" 2>/dev/null || git checkout --quiet -B "${ref#origin/}" "$ref"
git reset --hard "$ref"

echo "==> Pulling updated third-party images"
docker compose pull --ignore-buildable

echo "==> Rebuilding + restarting"
docker compose up -d --build --remove-orphans

echo "==> Pruning dangling images"
docker image prune -f >/dev/null

echo "==> Status"
docker compose ps
