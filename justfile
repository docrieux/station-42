# Station 42 task runner.  Run `just` to list recipes.
# Recipes use bash (Git Bash on Windows, native bash on the Pi).

set shell := ["bash", "-cu"]
set dotenv-load := true

# Compose files that make up the full stack. Add a line when you add a tool.
compose := "-f compose.yaml"

# Same, plus the local-testing overlay (see docs/local-testing.md). Uses .env if
# present, else .env.example -- like `check`, so it works on a fresh clone.
_dclocal := "docker compose --env-file " + ( if path_exists(".env") == "true" { ".env" } else { ".env.example" } ) + " -f compose.yaml -f compose.local.yaml"

_default:
    @just --list

# ---- Stack control -------------------------------------------------------------

# Start (or update) the whole stack in the background.
up:
    docker compose {{compose}} up -d --build

# Stop and remove the whole stack (volumes are kept).
down:
    docker compose {{compose}} down

# Restart one service, e.g. `just restart caddy`.
restart svc:
    docker compose {{compose}} restart {{svc}}

# Tail logs for one service, e.g. `just logs hello`.
logs svc:
    docker compose {{compose}} logs -f --tail=100 {{svc}}

# Show container status.
ps:
    docker compose {{compose}} ps

# Pull newer images for the off-the-shelf services.
pull:
    docker compose {{compose}} pull

# Validate the merged compose config without starting anything.
# Uses .env if present, otherwise .env.example so it works on a fresh clone.
check:
    docker compose --env-file {{ if path_exists(".env") == "true" { ".env" } else { ".env.example" } }} {{compose}} config -q && echo "compose OK"

# ---- Local test stack (this PC, not the Pi) --------------------------------

# Build + run the whole stack on this PC (127.0.0.1 ports + Caddy internal CA).
up-local:
    {{_dclocal}} up -d --build

# Stop and remove the local stack (state under infra/caddy/*-local is kept).
down-local:
    {{_dclocal}} down

# Local stack container + health status.
ps-local:
    {{_dclocal}} ps

# Tail one local service's logs, e.g. `just logs-local caddy`.
logs-local svc:
    {{_dclocal}} logs -f --tail=100 {{svc}}

# ---- Deploy (run on the Pi) --------------------------------------------------

# Pull the latest commit and roll the stack forward.
deploy:
    ./infra/scripts/deploy.sh

# Snapshot all named volumes to ./backups/.
backup:
    ./infra/scripts/backup.sh

# ---- Python development ------------------------------------------------------

# Install / sync the workspace virtualenv (every app + package).
sync:
    uv sync --all-packages

# Run the full test suite.
test:
    uv run --all-packages pytest

# Lint + format check (no changes written).
lint:
    uv run --all-packages ruff check .
    uv run --all-packages ruff format --check .

# Auto-format and auto-fix.
fmt:
    uv run --all-packages ruff format .
    uv run --all-packages ruff check --fix .

# Scaffold a new custom app from the template: `just new-app notes`
new-app name:
    ./infra/scripts/new-app.sh {{name}}
