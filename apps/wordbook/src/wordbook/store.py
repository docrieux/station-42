"""SQLite persistence for the saved dictionary.

One table, primary key ``(language, word)`` so the same spelling can live in both
the Spanish and English sections. The full upstream JSON is kept verbatim in
``raw`` and re-parsed on read, so the normalized model can change without a
re-fetch. Stdlib :mod:`sqlite3` only; a fresh connection per call (the file is
local and the workload tiny).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    word     TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('es', 'en')),
    added_at TEXT NOT NULL,
    source   TEXT NOT NULL,
    raw      TEXT NOT NULL,
    PRIMARY KEY (language, word)
)
"""

# Persistent lookup cache -- a word is only ever fetched from a source once
# (see wordbook.sources.lookup). `kind` is 'ok' (raw = upstream JSON) or
# 'notfound' (raw = the suggestions list).
_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS lookup_cache (
    language  TEXT NOT NULL,
    word      TEXT NOT NULL,
    kind      TEXT NOT NULL CHECK (kind IN ('ok', 'notfound')),
    source    TEXT NOT NULL DEFAULT '',
    raw       TEXT NOT NULL DEFAULT '',
    cached_at TEXT NOT NULL,
    PRIMARY KEY (language, word)
)
"""

# sort key -> ORDER BY clause. The API layer validates the key against a
# StrEnum; this dict is the second guard against interpolating anything else.
_ORDER_BY = {
    "alpha_asc": "word COLLATE NOCASE ASC",
    "alpha_desc": "word COLLATE NOCASE DESC",
    "added_asc": "added_at ASC, word COLLATE NOCASE ASC",
    "added_desc": "added_at DESC, word COLLATE NOCASE ASC",
}

_db_path: str | None = None


def init_db(path: str) -> None:
    """Create the parent dir, the table, and switch the file to WAL. Idempotent."""
    global _db_path
    _db_path = path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with _cursor() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_SCHEMA)
        conn.execute(_CACHE_SCHEMA)


def _connect() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("wordbook.store.init_db() has not been called")
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _cursor() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert(*, word: str, language: str, source: str, raw: str, added_at: str | None = None) -> bool:
    """Insert the word if absent. Returns True when a row was created.

    A re-bookmark keeps the original ``added_at`` (``DO NOTHING``) and returns
    False.
    """
    added_at = added_at or datetime.now(UTC).isoformat()
    with _cursor() as conn:
        cur = conn.execute(
            "INSERT INTO entries (word, language, added_at, source, raw) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(language, word) DO NOTHING",
            (word, language, added_at, source, raw),
        )
        return cur.rowcount > 0


def put(*, word: str, language: str, source: str, raw: str, added_at: str | None = None) -> str:
    """Create the entry, or replace its ``source`` + ``raw`` if the key exists.

    Returns ``"created"`` or ``"updated"``. An update keeps the original
    ``added_at`` (so a re-edited word stays where it is in the "by time added"
    sort). Used for hand-written / edited entries; bookmarking still uses
    :func:`upsert` (insert-if-absent).
    """
    with _cursor() as conn:
        exists = conn.execute(
            "SELECT 1 FROM entries WHERE language = ? AND word = ?", (language, word)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE entries SET source = ?, raw = ? WHERE language = ? AND word = ?",
                (source, raw, language, word),
            )
            return "updated"
        conn.execute(
            "INSERT INTO entries (word, language, added_at, source, raw) VALUES (?, ?, ?, ?, ?)",
            (word, language, added_at or datetime.now(UTC).isoformat(), source, raw),
        )
        return "created"


def list_entries(language: str, sort: str) -> list[sqlite3.Row]:
    """Rows for one language, ordered by one of the four ``_ORDER_BY`` keys."""
    order_by = _ORDER_BY[sort]  # KeyError on anything not in the whitelist
    with _cursor() as conn:
        return conn.execute(
            "SELECT word, language, added_at, source, raw FROM entries "
            f"WHERE language = ? ORDER BY {order_by}",
            (language,),
        ).fetchall()


def get_entry(language: str, word: str) -> sqlite3.Row | None:
    with _cursor() as conn:
        return conn.execute(
            "SELECT word, language, added_at, source, raw FROM entries "
            "WHERE language = ? AND word = ?",
            (language, word),
        ).fetchone()


def delete_entry(language: str, word: str) -> bool:
    """Returns True when a row was removed."""
    with _cursor() as conn:
        cur = conn.execute("DELETE FROM entries WHERE language = ? AND word = ?", (language, word))
        return cur.rowcount > 0


def count(language: str) -> int:
    with _cursor() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM entries WHERE language = ?", (language,)
        ).fetchone()
        return int(row["n"])


# --------------------------------------------------------------------------- #
# Persistent lookup cache                                                    #
# --------------------------------------------------------------------------- #


def cache_get(language: str, word: str) -> sqlite3.Row | None:
    with _cursor() as conn:
        return conn.execute(
            "SELECT kind, source, raw, cached_at FROM lookup_cache WHERE language = ? AND word = ?",
            (language, word),
        ).fetchone()


def cache_put(*, language: str, word: str, kind: str, source: str = "", raw: str = "") -> None:
    with _cursor() as conn:
        conn.execute(
            "INSERT INTO lookup_cache (language, word, kind, source, raw, cached_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(language, word) DO UPDATE SET "
            "kind = excluded.kind, source = excluded.source, raw = excluded.raw, "
            "cached_at = excluded.cached_at",
            (language, word, kind, source, raw, datetime.now(UTC).isoformat()),
        )


def cache_clear() -> None:
    with _cursor() as conn:
        conn.execute("DELETE FROM lookup_cache")
