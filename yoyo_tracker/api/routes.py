"""JSON REST API routes.

Each handler is a thin translation: validate input via Pydantic, call a ``core``
function, return the result. No business logic lives here.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from yoyo_tracker.api.deps import get_conn
from yoyo_tracker.core import db
from yoyo_tracker.core.models import (
    WishlistItemIn,
    WishlistItemOut,
    YoyoIn,
    YoyoOut,
)

router = APIRouter(prefix="/api", tags=["api"])


# ---- Collection ----------------------------------------------------------------


@router.get("/collection", response_model=list[YoyoOut])
def get_collection(
    q: str = Query("", description="Filter by name or brand substring."),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[YoyoOut]:
    return db.list_collection(conn, q)


@router.post("/collection", response_model=YoyoOut, status_code=201)
def add_to_collection(
    yoyo: YoyoIn,
    conn: sqlite3.Connection = Depends(get_conn),
) -> YoyoOut:
    return db.add_yoyo(conn, yoyo)


@router.delete("/collection/{yoyo_id}", status_code=204)
def delete_from_collection(
    yoyo_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    db.remove_yoyo(conn, yoyo_id)


# ---- Wishlist ------------------------------------------------------------------


@router.get("/wishlist", response_model=list[WishlistItemOut])
def get_wishlist(
    q: str = Query("", description="Filter by name or brand substring."),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[WishlistItemOut]:
    return db.list_wishlist(conn, q)


@router.post("/wishlist", response_model=WishlistItemOut, status_code=201)
def add_to_wishlist(
    item: WishlistItemIn,
    conn: sqlite3.Connection = Depends(get_conn),
) -> WishlistItemOut:
    return db.add_wishlist_item(conn, item)


@router.delete("/wishlist/{item_id}", status_code=204)
def delete_from_wishlist(
    item_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    db.remove_wishlist_item(conn, item_id)


@router.post("/wishlist/{item_id}/acquire", response_model=YoyoOut, status_code=201)
def acquire_wishlist_item(
    item_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> YoyoOut:
    return db.acquire(conn, item_id)
