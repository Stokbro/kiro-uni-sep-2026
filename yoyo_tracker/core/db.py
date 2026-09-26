"""SQLite persistence for the yoyo tracker.

All functions take an explicit ``sqlite3.Connection`` so callers (and tests) control
the database. Business invariants are enforced here, in the core, not in the API layer:

1. A yoyo name is never in both the collection and the wishlist at the same time.
2. ``acquire`` moves a yoyo from wishlist to collection atomically.

Queries are always parameterized.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from yoyo_tracker.core.models import (
    WishlistItemIn,
    WishlistItemOut,
    YoyoIn,
    YoyoOut,
)

DEFAULT_DB_PATH = Path.home() / ".yoyo-tracker" / "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    colorway TEXT,
    condition TEXT CHECK(condition IN ('mint', 'good', 'played')) DEFAULT 'good',
    date_acquired TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    max_price REAL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


# ---- Exceptions ----------------------------------------------------------------


class YoyoError(Exception):
    """Base class for domain errors."""


class YoyoNotFound(YoyoError):
    """Raised when a referenced yoyo does not exist."""


class DuplicateYoyo(YoyoError):
    """Raised when adding a yoyo that would violate the mutual-exclusion invariant."""


# ---- Connection management -----------------------------------------------------


def resolve_db_path() -> Path:
    """Return the configured database path (``YOYO_DB_PATH`` env var or default)."""
    env = os.environ.get("YOYO_DB_PATH")
    return Path(env) if env else DEFAULT_DB_PATH


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a connection with sensible defaults and ensure the schema exists.

    ``db_path`` of ``":memory:"`` gives an ephemeral database, handy for tests.
    """
    if db_path is None:
        db_path = resolve_db_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI resolves the per-request connection dependency
    # on a threadpool thread but may run an async handler body on the event-loop
    # thread. The connection is never shared across concurrent requests, so relaxing
    # the same-thread guard is safe here.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not already exist."""
    conn.executescript(SCHEMA)
    conn.commit()


# ---- Helpers -------------------------------------------------------------------


def _name_in_collection(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM collection WHERE name = ? LIMIT 1", (name,)
    ).fetchone()
    return row is not None


def _name_in_wishlist(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM wishlist WHERE name = ? LIMIT 1", (name,)
    ).fetchone()
    return row is not None


# ---- Collection ----------------------------------------------------------------


def add_yoyo(conn: sqlite3.Connection, yoyo: YoyoIn) -> YoyoOut:
    """Add a yoyo to the collection.

    Enforces invariant 1: a name in the wishlist cannot also enter the collection.
    """
    if _name_in_wishlist(conn, yoyo.name):
        raise DuplicateYoyo(
            f"{yoyo.name!r} is on the wishlist; acquire it instead of adding directly."
        )
    cur = conn.execute(
        """
        INSERT INTO collection (name, brand, colorway, condition, date_acquired, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            yoyo.name,
            yoyo.brand,
            yoyo.colorway,
            yoyo.condition,
            yoyo.date_acquired,
            yoyo.notes,
        ),
    )
    conn.commit()
    return get_yoyo(conn, int(cur.lastrowid))


def get_yoyo(conn: sqlite3.Connection, yoyo_id: int) -> YoyoOut:
    row = conn.execute("SELECT * FROM collection WHERE id = ?", (yoyo_id,)).fetchone()
    if row is None:
        raise YoyoNotFound(f"No yoyo with id {yoyo_id}")
    return YoyoOut(**dict(row))


def list_collection(conn: sqlite3.Connection, query: str = "") -> list[YoyoOut]:
    """List collection yoyos, optionally filtered by a name/brand substring.

    An empty query returns everything.
    """
    if query:
        like = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM collection WHERE name LIKE ? OR brand LIKE ? ORDER BY id",
            (like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM collection ORDER BY id").fetchall()
    return [YoyoOut(**dict(r)) for r in rows]


def remove_yoyo(conn: sqlite3.Connection, yoyo_id: int) -> None:
    cur = conn.execute("DELETE FROM collection WHERE id = ?", (yoyo_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise YoyoNotFound(f"No yoyo with id {yoyo_id}")


# ---- Wishlist ------------------------------------------------------------------


def add_wishlist_item(conn: sqlite3.Connection, item: WishlistItemIn) -> WishlistItemOut:
    """Add a yoyo to the wishlist.

    Enforces invariant 1: a name already in the collection cannot go on the wishlist.
    """
    if _name_in_collection(conn, item.name):
        raise DuplicateYoyo(f"{item.name!r} is already in the collection.")
    cur = conn.execute(
        "INSERT INTO wishlist (name, brand, max_price, notes) VALUES (?, ?, ?, ?)",
        (item.name, item.brand, item.max_price, item.notes),
    )
    conn.commit()
    return get_wishlist_item(conn, int(cur.lastrowid))


def get_wishlist_item(conn: sqlite3.Connection, item_id: int) -> WishlistItemOut:
    row = conn.execute("SELECT * FROM wishlist WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise YoyoNotFound(f"No wishlist item with id {item_id}")
    return WishlistItemOut(**dict(row))


def list_wishlist(conn: sqlite3.Connection, query: str = "") -> list[WishlistItemOut]:
    if query:
        like = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM wishlist WHERE name LIKE ? OR brand LIKE ? ORDER BY id",
            (like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM wishlist ORDER BY id").fetchall()
    return [WishlistItemOut(**dict(r)) for r in rows]


def remove_wishlist_item(conn: sqlite3.Connection, item_id: int) -> None:
    cur = conn.execute("DELETE FROM wishlist WHERE id = ?", (item_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise YoyoNotFound(f"No wishlist item with id {item_id}")


def acquire(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    condition: str = "good",
    date_acquired: str | None = None,
) -> YoyoOut:
    """Move a wishlist item into the collection atomically (invariant 2).

    Either both the wishlist delete and the collection insert happen, or neither does.
    """
    item = get_wishlist_item(conn, item_id)  # raises YoyoNotFound if missing
    try:
        conn.execute("BEGIN")
        conn.execute(
            """
            INSERT INTO collection
                (name, brand, colorway, condition, date_acquired, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item.name, item.brand, None, condition, date_acquired, item.notes),
        )
        conn.execute("DELETE FROM wishlist WHERE id = ?", (item_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute(
        "SELECT * FROM collection WHERE name = ? ORDER BY id DESC LIMIT 1",
        (item.name,),
    ).fetchone()
    return YoyoOut(**dict(row))
