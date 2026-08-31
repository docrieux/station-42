"""Minimal, dependency-free logging setup.

Containers log to stdout/stderr and Docker captures that, so all we need is a
sensible line format and a configurable level.
"""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once. Safe to call at app startup.

    ``level`` is a name like ``"INFO"`` or ``"DEBUG"`` (case-insensitive).
    """
    resolved = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(resolved)

    # Replace any existing handlers so repeated calls stay idempotent.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)

    # uvicorn installs its own handlers; let them propagate to ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
