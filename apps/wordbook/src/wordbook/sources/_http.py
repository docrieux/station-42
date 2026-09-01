"""Shared HTTP helper for the source clients: one GET with retry + backoff."""

from __future__ import annotations

import asyncio

import httpx

from wordbook.models import RateLimited, SourceError


def _retry_after(response: httpx.Response) -> int | None:
    """Seconds until the limit resets, from the ``Retry-After`` header or body."""
    header = response.headers.get("retry-after", "")
    if header.isdigit():
        return int(header)
    try:
        value = response.json().get("retry_after")
    except (ValueError, AttributeError):
        return None
    return int(value) if isinstance(value, (int, float)) else None


async def get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    retries: int = 1,
) -> httpx.Response:
    """GET *url*, retrying transient failures (connection error, 5xx).

    A read timeout is **not** retried (the server took the request and then
    stalled). A 429 is **not** retried either — it raises :class:`RateLimited`
    with the reset time so the caller can show it. Returns the response for any
    other status below 500 (the caller handles 404 / 4xx). Raises
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
            if response.status_code == 429:
                raise RateLimited(_retry_after(response))
            if response.status_code < 500:
                return response
            detail = f"HTTP {response.status_code}"
        if attempt < retries:
            await asyncio.sleep(delay)
            delay *= 2
    raise SourceError(detail)
