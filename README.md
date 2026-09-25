# Yoyo Collection Tracker

A web app for yoyo enthusiasts to manage their collection, track a wishlist, check
store availability, and follow community news from Reddit.

## Features

- **Collection** — record the yoyos you own (brand, colorway, condition, notes)
- **Wishlist** — track yoyos you want, with a max price; acquire moves them to the collection
- **Availability** — check whether a yoyo is in stock at supported stores
- **Community feed** — recent posts from r/Throwers and r/Yoyo, optionally filtered to
  yoyos in your collection or wishlist

## Architecture

Three cleanly separated layers:

- `yoyo_tracker/core/` — pure business logic (models, DB, availability, reddit). No web imports.
- `yoyo_tracker/api/` — a thin FastAPI layer translating HTTP to core calls.
- `yoyo_tracker/api/templates/` — Jinja2 server-rendered pages with minimal JS.

See [`.kiro/specs/yoyo-tracker.md`](.kiro/specs/yoyo-tracker.md) for the full spec.

## Requirements

- Python 3.11+

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

## Running

```bash
yoyo-tracker
# or
uvicorn yoyo_tracker.api.app:app --reload
```

Then open:

- App: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

## Configuration

- `YOYO_DB_PATH` — path to the SQLite database. Defaults to `~/.yoyo-tracker/data.db`.

## Testing

```bash
pytest
```

Property-based tests (via [Hypothesis](https://hypothesis.readthedocs.io/)) verify the
core invariants — for example, a yoyo is never in both the collection and the wishlist.

## Development

- Format & lint with [ruff](https://docs.astral.sh/ruff/): `ruff format . && ruff check .`
- Conventions the project follows live in [`.kiro/steering/conventions.md`](.kiro/steering/conventions.md).
