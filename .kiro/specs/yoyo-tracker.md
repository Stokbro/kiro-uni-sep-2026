# Feature Spec: Yoyo Collection Tracker

## Overview

A web application that helps yoyo enthusiasts manage their collection, track their
wishlist, monitor store availability, and stay up to date with community news from
Reddit. Built as a testable Python core with a FastAPI REST layer and a thin web
frontend.

## Architecture

Three layers, cleanly separated so the core stays pure and testable:

```
┌─────────────────────────────────────────┐
│  Frontend (thin)                         │
│  Jinja2 server-rendered templates + a    │
│  little vanilla JS (fetch)               │
└──────────────────┬──────────────────────┘
                   │ HTTP / JSON
┌──────────────────▼──────────────────────┐
│  FastAPI layer (api/)                    │
│  Routes + Pydantic request/response      │
│  models. No business logic here — it     │
│  calls into core.                        │
└──────────────────┬──────────────────────┘
                   │ function calls
┌──────────────────▼──────────────────────┐
│  Core (core/) — PURE, no web imports     │
│  models, db, availability, reddit        │
│  This is what property-based tests hit.  │
└──────────────────────────────────────────┘
```

The key discipline: **all business rules live in `core/` as plain functions.**
The API layer is a thin translation of HTTP ⇆ core calls, so the business logic
can be verified in isolation without HTTP plumbing.

## Requirements

### R1 — Collection Management
- Add a yoyo with: name, brand, colorway, condition (mint/good/played), date
  acquired, optional notes
- Remove a yoyo from the collection
- List all yoyos; search by name or brand
- A yoyo cannot be in both the collection and the wishlist simultaneously

### R2 — Wishlist Management
- Add a yoyo to the wishlist with: name, brand, max price, optional notes
- Remove from the wishlist
- List all wishlist items
- Acquiring a wishlist yoyo moves it to the collection atomically

### R3 — Availability Tracking
- Check availability of a yoyo by name across supported stores
- Status is one of: `in-stock`, `out-of-stock`, `unknown`
- Results include store name, price, and URL when available
- Supported store (prototype): YoyoExpert

### R4 — Reddit Community Feed
- Fetch recent posts from r/Throwers and r/Yoyo
- Filtered view: only posts mentioning yoyos in the collection or wishlist
- Unfiltered view available
- Read-only access; no user credentials required

### R5 — Persistence
- SQLite database at `~/.yoyo-tracker/data.db`, auto-created on first run
- Path overridable via `YOYO_DB_PATH` env var (so tests use a temp DB)

### R6 — Web Interface
- FastAPI app served with uvicorn
- Pages:
  - `/` — dashboard: collection grid + wishlist + quick stats
  - `/collection` — full collection with add/remove
  - `/wishlist` — wishlist with add/remove/acquire
  - `/availability?name=...` — availability check results
  - `/feed` and `/feed?all=true` — Reddit feed
- Interactive API docs auto-served at `/docs` (FastAPI/OpenAPI)

### R7 — REST API
JSON endpoints backing every page:
- `GET /api/collection` · `POST /api/collection` · `DELETE /api/collection/{id}`
- `GET /api/collection/search?q=...`
- `GET /api/wishlist` · `POST /api/wishlist` · `DELETE /api/wishlist/{id}`
- `POST /api/wishlist/{id}/acquire`
- `GET /api/availability?name=...`
- `GET /api/feed?all={bool}`

## Technical Design

### Stack
- Python 3.11+
- Web: **FastAPI** + **uvicorn** (ASGI)
- Validation: **Pydantic v2** (single source of truth for data invariants)
- Templates: **Jinja2** (server-rendered, minimal JS)
- Database: `sqlite3` (stdlib)
- HTTP client: **httpx** (async)
- HTML parsing: **beautifulsoup4** (store scraping)
- Reddit: read-only public JSON feed
- Testing: **pytest** + **hypothesis**

### Data Model

```sql
CREATE TABLE collection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    colorway TEXT,
    condition TEXT CHECK(condition IN ('mint', 'good', 'played')) DEFAULT 'good',
    date_acquired TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    max_price REAL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Pydantic Models (shared source of truth)

```python
Condition = Literal["mint", "good", "played"]
AvailabilityStatus = Literal["in-stock", "out-of-stock", "unknown"]

class YoyoIn(BaseModel):
    name: str
    brand: str
    colorway: str | None = None
    condition: Condition = "good"
    date_acquired: str | None = None
    notes: str | None = None

class WishlistItemIn(BaseModel):
    name: str
    brand: str
    max_price: float | None = None
    notes: str | None = None
```

### Project Structure

```
yoyo_tracker/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py          # Pydantic models, enums
│   ├── db.py              # SQLite CRUD — pure functions taking a connection
│   ├── availability.py    # YoyoExpert scraper (async)
│   └── reddit.py          # Reddit feed fetching + filtering
├── api/
│   ├── __init__.py
│   ├── app.py             # FastAPI app factory
│   ├── routes.py          # API + page routes
│   └── templates/         # Jinja2 templates
│       ├── base.html
│       ├── dashboard.html
│       ├── collection.html
│       ├── wishlist.html
│       └── feed.html
└── static/                # minimal CSS + JS
tests/
├── test_models.py
├── test_db.py
├── test_properties.py     # hypothesis property tests
└── test_api.py            # FastAPI TestClient
.kiro/
├── specs/yoyo-tracker.md  (this file)
├── steering/conventions.md
├── hooks/
├── agents/yoyo-tracker.json
└── settings/mcp.json
pyproject.toml
README.md
```

## Implementation Tasks

1. [ ] Project scaffold: `pyproject.toml`, package dirs, README
2. [ ] `core/models.py` — Pydantic models + `Condition`/`AvailabilityStatus` literals
3. [ ] `core/db.py` — SQLite schema init + CRUD for collection and wishlist
4. [ ] Enforce the collection/wishlist mutual-exclusion invariant in `db.py`
5. [ ] `api/app.py` + `api/routes.py` — FastAPI app, JSON endpoints
6. [ ] Jinja2 templates + minimal static assets (thin frontend)
7. [ ] `core/availability.py` — async YoyoExpert scraper
8. [ ] `core/reddit.py` — Reddit feed with collection/wishlist filtering
9. [ ] `tests/test_properties.py` — property-based tests
10. [ ] `tests/test_api.py` — FastAPI TestClient integration tests
11. [ ] `README.md` — setup, usage, and API overview

## Invariants (verified by property-based tests)

- A yoyo name in the collection is never simultaneously in the wishlist
- `list_collection()` always returns exactly what was added minus what was removed
- Availability status is always one of `in-stock`, `out-of-stock`, `unknown`
- `acquire(name)` always removes from wishlist AND adds to collection (atomic — both or neither)
- Search with empty query returns all items; search with a name returns only matching items
- Round-trip: a yoyo added then read back has identical field values
- Adding a duplicate-named yoyo behaves consistently (define: reject or allow — decided in design)
