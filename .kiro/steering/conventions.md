# Yoyo Tracker — Project Conventions

Persistent guidance for building the Yoyo Collection Tracker. Follow these
consistently so the codebase stays coherent.

## Language & Tooling

- Python **3.11+**. Use modern syntax: `X | None` unions, `list[str]` /
  `dict[str, int]` builtins (never `typing.List`/`Optional`), `match` where it reads
  well.
- Type-hint **every** function signature and public attribute. Code should pass a
  strict type checker.
- Format with **ruff format**; lint with **ruff**. No unused imports, no wildcard
  imports.
- Dependencies are declared in `pyproject.toml` only. Pin nothing tighter than a
  minor version unless there's a reason.

## Architecture — the layering rule

Three layers, and the boundaries are strict:

- **`core/`** holds ALL business logic as plain, synchronous-where-possible
  functions. `core/` must **never** import from `api/`, FastAPI, or Jinja2. It
  depends only on the standard library, Pydantic, and its own modules.
- **`api/`** is a thin translation layer: parse the HTTP request, call a `core`
  function, shape the response. **No business rules in `api/`.** If you're writing a
  conditional about yoyo data in a route handler, it belongs in `core/`.
- **Frontend** (Jinja2 templates + minimal vanilla JS) only renders data the API
  already prepared. No business logic in templates.

Rationale: this keeps `core/` pure so it can be property-tested in isolation without
spinning up HTTP.

## Data & Validation

- **Pydantic v2** models are the single source of truth for data shapes and
  invariants. Define allowed values as `Literal` types:
  - `Condition = Literal["mint", "good", "played"]`
  - `AvailabilityStatus = Literal["in-stock", "out-of-stock", "unknown"]`
- The database layer (`core/db.py`) takes an explicit `sqlite3.Connection` argument
  rather than reaching for a global connection — this makes tests trivial (pass a
  temp/in-memory connection).
- The DB path comes from `YOYO_DB_PATH` env var, falling back to
  `~/.yoyo-tracker/data.db`. Never hardcode an absolute path.
- SQL uses **parameterized queries** always (`?` placeholders). Never f-string user
  values into SQL.

## Core Invariants (must always hold)

These are non-negotiable business rules. Enforce them in `core/`, not in the API:

1. A yoyo name in the collection is **never** simultaneously in the wishlist.
2. `acquire(name)` moves a yoyo from wishlist to collection **atomically** — both
   changes happen or neither does (wrap in a transaction).
3. Availability status is **always** one of the three `AvailabilityStatus` values.
4. Listing after a series of adds/removes returns exactly the surviving set.

## Async

- External I/O (store scraping, Reddit fetching) is **async** using `httpx.AsyncClient`.
- Pure data operations (`core/db.py`, `core/models.py`) stay **synchronous** — SQLite
  is fast and local; async there adds noise without benefit.
- FastAPI route handlers that call async core functions are `async def`; those that
  only touch the sync DB layer may be plain `def`.

## Testing

- **pytest** for all tests; tests live in `tests/`.
- **hypothesis** for property-based tests of core logic (`tests/test_properties.py`) —
  test the invariants above, not hand-picked examples.
- API tests use FastAPI's `TestClient` with a temp DB via `YOYO_DB_PATH`.
- Every test is isolated: fresh DB per test, no shared mutable state, no network calls
  (mock external HTTP).
- A feature isn't done until its tests pass.

## Error Handling

- `core/` raises specific exceptions (e.g. `YoyoNotFound`, `DuplicateYoyo`) — define
  them in `core/`. Don't raise bare `Exception`.
- The API layer catches core exceptions and maps them to proper HTTP status codes
  (404, 409, 422). Never leak a stack trace to the client.

## Naming & Style

- Modules and functions: `snake_case`. Classes and Pydantic models: `PascalCase`.
- Pydantic input models end in `In` (e.g. `YoyoIn`); output/response models end in
  `Out` (e.g. `YoyoOut`).
- Prefer small, single-purpose functions. If a function needs a comment to explain a
  block, that block probably wants to be its own named function.
- Docstrings on public functions state what and why, not how.

## Commits

- Small, focused commits with imperative subject lines
  ("Add wishlist acquire endpoint", not "added stuff").
- Keep the working tree clean; run tests before committing.
