import pytest
from wordbook import store

RAW = '{"x": 1}'


def test_upsert_is_idempotent():
    assert store.upsert(word="casa", language="es", source="rae-api.com", raw=RAW) is True
    assert store.upsert(word="casa", language="es", source="rae-api.com", raw=RAW) is False
    assert store.count("es") == 1


def test_same_spelling_in_both_sections():
    store.upsert(word="no", language="es", source="rae-api.com", raw=RAW)
    store.upsert(word="no", language="en", source="dictionaryapi.dev", raw=RAW)
    assert store.count("es") == 1
    assert store.count("en") == 1


def test_rebookmark_keeps_original_added_at():
    store.upsert(
        word="sol", language="es", source="s", raw=RAW, added_at="2020-01-01T00:00:00+00:00"
    )
    store.upsert(word="sol", language="es", source="s", raw='{"x": 2}')
    row = store.get_entry("es", "sol")
    assert row["added_at"] == "2020-01-01T00:00:00+00:00"
    assert row["raw"] == RAW  # DO NOTHING -> raw unchanged too


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("alpha_asc", ["ave", "casa", "zorro"]),
        ("alpha_desc", ["zorro", "casa", "ave"]),
        ("added_asc", ["casa", "zorro", "ave"]),
        ("added_desc", ["ave", "zorro", "casa"]),
    ],
)
def test_sort_orders(sort, expected):
    def add(word: str, added_at: str) -> None:
        store.upsert(word=word, language="es", source="s", raw=RAW, added_at=added_at)

    add("casa", "2021-01-01T00:00:00+00:00")
    add("zorro", "2021-02-01T00:00:00+00:00")
    add("ave", "2021-03-01T00:00:00+00:00")
    assert [row["word"] for row in store.list_entries("es", sort)] == expected


def test_list_is_scoped_by_language():
    store.upsert(word="casa", language="es", source="s", raw=RAW)
    store.upsert(word="house", language="en", source="s", raw=RAW)
    assert [r["word"] for r in store.list_entries("es", "alpha_asc")] == ["casa"]


def test_delete():
    store.upsert(word="casa", language="es", source="s", raw=RAW)
    assert store.delete_entry("es", "casa") is True
    assert store.delete_entry("es", "casa") is False
    assert store.count("es") == 0
