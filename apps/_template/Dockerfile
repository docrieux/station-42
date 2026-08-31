# syntax=docker/dockerfile:1
#
# Build context is the REPO ROOT (see compose.yaml: build.context = ../..), so the
# uv workspace and the shared `packages/` are visible during `uv sync`.

FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Workspace metadata + shared packages first: cached unless they change.
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/appname/ apps/appname/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package appname

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status == 200 else 1)"
CMD ["uvicorn", "appname.main:app", "--host", "0.0.0.0", "--port", "8000"]
