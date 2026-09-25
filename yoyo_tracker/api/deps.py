"""FastAPI dependencies, kept separate so routes and the app factory can both import
them without creating an import cycle.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from yoyo_tracker.core import db


def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a per-request database connection, closed when the request ends."""
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()
