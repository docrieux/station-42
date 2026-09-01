#!/usr/bin/env bash
# Scaffold a new custom app from apps/_template.
#
#   ./infra/scripts/new-app.sh notes
#
# Name must be a valid Python identifier: lowercase letters, digits, underscores,
# starting with a letter.
set -euo pipefail

name="${1:-}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -z "$name" ]]; then
    echo "usage: $0 <app-name>" >&2
    exit 2
fi
if [[ ! "$name" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo "error: '$name' must match ^[a-z][a-z0-9_]*\$ (lowercase, digits, _)" >&2
    exit 2
fi

src="$repo_root/apps/_template"
dst="$repo_root/apps/$name"
name_upper="$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')"

if [[ -e "$dst" ]]; then
    echo "error: apps/$name already exists" >&2
    exit 1
fi

cp -r "$src" "$dst"
rm -f "$dst/service.compose.snippet.yaml"
mv "$dst/src/appname" "$dst/src/$name"

# Substitute placeholders. APPNAME_ (env prefix) first, then the bare token.
while IFS= read -r -d '' file; do
    sed -i "s/APPNAME_/${name_upper}_/g; s/appname/${name}/g" "$file"
done < <(find "$dst" -type f -print0)

echo "Created apps/$name  —  dual-UI app: / -> /d/ or /m/, JSON at /api/, probe at /healthz"
echo "  edit:  src/$name/api.py  and  src/$name/web/templates/{desktop,mobile}/index.html"
echo
echo "Registering the workspace member (uv sync)..."
( cd "$repo_root" && uv sync --all-packages )

# The template's import order is only isort-clean for names that sort before
# "station_common"; normalise the generated app so `just lint` passes for any name.
( cd "$repo_root" && uv run ruff check --fix --quiet "apps/$name" && uv run ruff format --quiet "apps/$name" )

cat <<EOF

--------------------------------------------------------------------------------
1. Add this block under 'services:' in compose.yaml:

  ${name}:
    build:
      context: .
      dockerfile: apps/${name}/Dockerfile
    image: station42/${name}:latest
    restart: unless-stopped
    environment:
      LOG_LEVEL: \${LOG_LEVEL:-INFO}
      TZ: \${TZ:-UTC}
    networks:
      - edge

2. Add this route inside the '*.{\$DUCKDNS_DOMAIN}' block in infra/caddy/Caddyfile
   (one route — the desktop/mobile split is internal; see docs/dual-ui.md):

    @${name} host ${name}.{\$DUCKDNS_DOMAIN}
    handle @${name} {
        reverse_proxy ${name}:8000
    }

3. Develop locally without Docker (/ redirects; try /d/ and /m/):

    uv run uvicorn ${name}.main:app --reload

4. Test the built image locally (see docs/local-testing.md):
   - add to compose.local.yaml under 'services:' (next free 127.0.0.1 port):

    ${name}:
      ports:
        - "127.0.0.1:8002:8000"

   - mirror the route into infra/caddy/Caddyfile.local, host
     ${name}.station42.localhost
   - just up-local   then open  http://localhost:8002/

5. Ship it:  just check && just test   then   just up   (on the Pi:  just deploy)
--------------------------------------------------------------------------------
EOF
