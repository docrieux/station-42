#!/usr/bin/env bash
# Snapshot all persistent state (bind-mounted ./**/data dirs + .env) into a
# timestamped tarball under ./backups/. Run on the Pi.
#
#   ./infra/scripts/backup.sh
#
# Restore: stop the stack, extract the tarball at the repo root, `just up`.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

stamp="$(date +%Y%m%d-%H%M%S)"
out="backups/station42-${stamp}.tar.gz"
mkdir -p backups

# Collect data dirs (services/*/data, infra/*/data) plus .env.
mapfile -t targets < <(find . -type d -name data -not -path './backups/*' | sed 's|^\./||')
[[ -f .env ]] && targets+=(".env")

if [[ ${#targets[@]} -eq 0 ]]; then
    echo "nothing to back up yet"
    exit 0
fi

echo "==> Archiving:"
printf '    %s\n' "${targets[@]}"
tar -czf "$out" "${targets[@]}"

echo "==> Wrote $out ($(du -h "$out" | cut -f1))"

# Keep the 14 most recent.
ls -1t backups/station42-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -v
