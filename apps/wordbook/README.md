# wordbook

A modifiable bilingual dictionary. Search a word in Spanish or English, read its
definition blocks, and bookmark it into a two-section personal dictionary that
re-sorts alphabetically or by time added.

| Language | Source | Key |
|---|---|---|
| Spanish (`es`) | [rae-api.com](https://rae-api.com) (unofficial RAE) | none — free tier is 10 req/min, 100 req/day; set `WORDBOOK_RAE_API_KEY` to lift it |
| English (`en`) | [freedictionaryapi.com](https://freedictionaryapi.com) (Wiktionary-derived) | none |

## API

| Method & path | Purpose |
|---|---|
| `GET /api/lookup?language=es|en&word=` | live source lookup — `404` `{word, suggestions}` when unknown, `429` `{retry_after, reset_at, reset_in}` + `Retry-After` when rate-limited, `502` when the source is down |
| `GET /api/dictionary?language=es|en&sort=` | saved words; `sort` ∈ `alpha_asc` `alpha_desc` `added_asc` `added_desc` |
| `GET /api/dictionary/{language}/{word}` | one saved entry — `404` if absent |
| `POST /api/dictionary` `{language, word}` | bookmark — server re-fetches from the source; `201` created / `200` already saved |
| `POST /api/entries` `{language, word, senses:[{text, part_of_speech?, example?}]}` | create or replace a **hand-written** entry (`source = "manual"`); `201` created / `200` replaced; `422` if no definition text |
| `DELETE /api/dictionary/{language}/{word}` | remove — `204` / `404` |

## UI

`/` redirects by device to `/d/` (desktop) or `/m/` (mobile). Search, bookmark,
sort, and — via the **"+ Add a word"** box in the section header or the **Edit**
toggle on any saved entry — hand-written definitions. Manual entries store their
normalized JSON directly (`source = "manual"`) and are re-parsed on read without
touching a source; editing a bookmarked entry converts it to a manual one.
Everything works with JavaScript disabled (full-page reloads).

## Storage

SQLite at `WORDBOOK_DB_PATH` (default `/data/wordbook.db`). `entries` holds the
saved dictionary keyed by `(language, word)`; `lookup_cache` is a persistent
cache of every source lookup. The full upstream JSON is stored verbatim and
re-parsed on read. `just backup` picks the file up via the `**/data/` bind mount.

### Quota / rate limits

rae-api.com's free tier is per source IP: **10 req/min, 100 req/day**, resetting
at 00:00 UTC (`429` responses carry `Retry-After`, surfaced in the UI as a live
countdown). `lookup_cache` keeps every successful lookup **forever** — a source
dictionary is effectively static — so the daily quota is only ever spent on a
word's *first* lookup, across restarts and redeploys. A confirmed "not found" is
trusted for `WORDBOOK_LOOKUP_CACHE_DAYS` (default 30) then re-checked. Set
`WORDBOOK_RAE_API_KEY` for the free Developer tier (5,000 req/day, per key).

## Local development

```bash
WORDBOOK_DB_PATH=./apps/wordbook/data/wordbook.db \
  uv run uvicorn wordbook.main:app --reload
```

## Deploy note — `/data` permissions

The container runs as uid **10001** (`USER app`). If Docker auto-creates the host
bind-mount dir it is owned by `root`, and SQLite writes fail. The repo ships
`apps/wordbook/data/.gitkeep` so the directory exists on clone; on the Pi make it
writable by the app user once:

```bash
sudo chown -R 10001 apps/wordbook/data
```

`just up-local` on Docker Desktop (Windows/macOS) is unaffected.
