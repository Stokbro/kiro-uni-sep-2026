"""JSON REST API routes.

Each handler is a thin translation: validate input via Pydantic, call a ``core``
function, return the result. No business logic lives here.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from yoyo_tracker.api.deps import get_conn
from yoyo_tracker.core import availability, db, reddit
from yoyo_tracker.core.models import (
    RedditPost,
    StoreResult,
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


@router.get("/collection/{yoyo_id}/availability", response_model=list[StoreResult])
async def get_availability(
    yoyo_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[StoreResult]:
    """Check store availability for a collection yoyo by its name.

    Raises ``YoyoNotFound`` (mapped to 404) if the id is unknown; the store lookup
    itself never fails — an unreachable store degrades to ``unknown`` in core.
    """
    yoyo = db.get_yoyo(conn, yoyo_id)
    return await availability.check_availability(yoyo.name)


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


# ---- Community feed ------------------------------------------------------------


@router.get("/feed", response_model=list[RedditPost])
async def get_feed(
    all: bool = Query(False, description="Return all posts, not just tracked matches."),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[RedditPost]:
    """Recent community posts. By default filtered to posts mentioning a tracked yoyo
    (collection + wishlist names); ``all=true`` returns the unfiltered feed.
    """
    posts = await reddit.fetch_feed()
    if all:
        return posts
    tracked = _tracked_names(conn)
    return reddit.filter_posts(posts, tracked)


def _tracked_names(conn: sqlite3.Connection) -> list[str]:
    """All names being tracked across collection and wishlist."""
    names = [y.name for y in db.list_collection(conn)]
    names += [w.name for w in db.list_wishlist(conn)]
    return names
