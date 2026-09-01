"""The common shape both dictionary sources are normalized into.

``rae-api.com`` (Spanish) and ``dictionaryapi.dev`` (English) return very
different JSON. Each source module parses its payload into an :class:`Entry`
made of :class:`Sense` blocks — one block per definition, which is also the unit
the UI renders and the dictionary sorts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Language = Literal["es", "en"]


class Sense(BaseModel):
    """One definition block."""

    number: int | None = None
    part_of_speech: str | None = None
    text: str
    examples: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    usage: str | None = None  # RAE usage label ("coloquial", "rare", ...); None for EN
    regions: list[str] = []  # RAE regions[].name
    domains: list[str] = []  # RAE fields[] ("Mús.", "Astron.", ...)


class Entry(BaseModel):
    """A headword and its senses, normalized from one source."""

    word: str
    language: Language
    source: str  # "rae-api.com" | "dictionaryapi.dev"
    source_url: str | None = None
    phonetics: list[str] = []  # EN IPA strings; [] for ES
    etymology: str | None = None
    senses: list[Sense]


class StoredEntry(Entry):
    """An :class:`Entry` re-parsed from the saved raw payload, plus its save time."""

    added_at: datetime


class WordNotFound(Exception):
    """The source has no entry for this word (HTTP 404 upstream)."""

    def __init__(self, word: str, suggestions: list[str] | None = None) -> None:
        super().__init__(f"no dictionary entry for {word!r}")
        self.word = word
        self.suggestions = suggestions or []


class SourceError(Exception):
    """The source failed for a reason other than 'not found' (5xx, 429, network)."""
