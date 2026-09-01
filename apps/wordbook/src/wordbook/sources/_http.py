"""Shared HTTP helper for the source clients: one GET with retry + backoff."""

from __future__ import annotations

import asyncio

import httpx

from wordbook.models import SourceError


async def get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    retries: int = 1,
) -> httpx.Response:
    """GET *url*, retrying transient failures (connection error, 5xx, 429).

    A read timeout is **not** retried — the server took the request and then
    stalled, so asking again only doubles the wait. Returns the response for any
    status below 500 (the caller handles 404 / 4xx). Raises
    :class:`~wordbook.models.SourceError` once the retries are used up.
    """
    delay = 0.5
    detail = "request failed"
    for attempt in range(retries + 1):
        try:
            response = await client.get(url, headers=headers)
        except httpx.ReadTimeout as exc:
            raise SourceError("the source stalled (read timeout)") from exc
        except httpx.RequestError as exc:
            detail = f"{type(exc).__name__}: {exc}".strip()
        else:
            if response.status_code < 500 and response.status_code != 429:
                return response
            detail = f"HTTP {response.status_code}"
        if attempt < retries:
            await asyncio.sleep(delay)
            delay *= 2
    raise SourceError(detail)
