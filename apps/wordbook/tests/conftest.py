"""Test setup: an isolated SQLite file and a clean cache for every test.

`WORDBOOK_DB_PATH` is pointed at a temp file before `wordbook.settings` is first
imported, so the app never touches `/data` during tests. The autouse fixture
resets the DB file and the in-process lookup cache between tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="wordbook-tests-"))
os.environ["WORDBOOK_DB_PATH"] = str(_TMP / "wordbook.db")


@pytest.fixture(autouse=True)
def _fresh_state() -> None:
    from wordbook import sources, store
    from wordbook.settings import settings

    db = Path(settings.db_path)
    for leftover in db.parent.glob(db.name + "*"):  # .db, .db-wal, .db-shm
        leftover.unlink()
    sources.clear_cache()
    store.init_db(settings.db_path)
    yield
