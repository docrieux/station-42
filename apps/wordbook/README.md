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
| `GET /api/lookup?language=es|en&word=` | live source lookup — `404` `{word, suggestions}` when unknown, `502` when the source is down |
| `GET /api/dictionary?language=es|en&sort=` | saved words; `sort` ∈ `alpha_asc` `alpha_desc` `added_asc` `added_desc` (default `added_desc`) |
| `POST /api/dictionary` `{language, word}` | bookmark — server re-fetches from the source; `201` created / `200` already saved |
| `DELETE /api/dictionary/{language}/{word}` | remove — `204` / `404` |

The dual-UI (`/`, `/d/`, `/m/`) is still the scaffold placeholder; the search /
result-box / bookmark / sort front-end is a later phase.

## Storage

SQLite at `WORDBOOK_DB_PATH` (default `/data/wordbook.db`), one table keyed by
`(language, word)`. The full upstream JSON is stored verbatim and re-parsed on
read. `just backup` picks the file up via the `**/data/` bind mount.

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
