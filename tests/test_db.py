"""Example-based tests for the SQLite persistence layer."""

from __future__ import annotations

import sqlite3

import pytest

from yoyo_tracker.core import db
from yoyo_tracker.core.models import WishlistItemIn, YoyoIn


def test_add_and_get_yoyo(conn: sqlite3.Connection) -> None:
    saved = db.add_yoyo(conn, YoyoIn(name="Shutter", brand="YoYoFactory"))
    assert saved.id > 0
    fetched = db.get_yoyo(conn, saved.id)
    assert fetched.name == "Shutter"
    assert fetched.brand == "YoYoFactory"


def test_list_collection_empty(conn: sqlite3.Connection) -> None:
    assert db.list_collection(conn) == []


def test_list_and_remove(conn: sqlite3.Connection) -> None:
    a = db.add_yoyo(conn, YoyoIn(name="Shutter", brand="YoYoFactory"))
    db.add_yoyo(conn, YoyoIn(name="Draupnir", brand="One Drop"))
    assert len(db.list_collection(conn)) == 2
    db.remove_yoyo(conn, a.id)
    remaining = db.list_collection(conn)
    assert len(remaining) == 1
    assert remaining[0].name == "Draupnir"


def test_remove_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(db.YoyoNotFound):
        db.remove_yoyo(conn, 999)


def test_search_collection(conn: sqlite3.Connection) -> None:
    db.add_yoyo(conn, YoyoIn(name="Shutter", brand="YoYoFactory"))
    db.add_yoyo(conn, YoyoIn(name="Draupnir", brand="One Drop"))
    assert len(db.list_collection(conn, "shut")) == 1
    assert len(db.list_collection(conn, "one drop")) == 1
    assert len(db.list_collection(conn, "")) == 2


def test_wishlist_add_and_list(conn: sqlite3.Connection) -> None:
    db.add_wishlist_item(conn, WishlistItemIn(name="Draupnir", brand="One Drop"))
    items = db.list_wishlist(conn)
    assert len(items) == 1
    assert items[0].name == "Draupnir"


def test_cannot_wishlist_something_in_collection(conn: sqlite3.Connection) -> None:
    db.add_yoyo(conn, YoyoIn(name="Shutter", brand="YoYoFactory"))
    with pytest.raises(db.DuplicateYoyo):
        db.add_wishlist_item(conn, WishlistItemIn(name="Shutter", brand="YoYoFactory"))


def test_cannot_add_collection_item_thats_wishlisted(conn: sqlite3.Connection) -> None:
    db.add_wishlist_item(conn, WishlistItemIn(name="Draupnir", brand="One Drop"))
    with pytest.raises(db.DuplicateYoyo):
        db.add_yoyo(conn, YoyoIn(name="Draupnir", brand="One Drop"))


def test_acquire_moves_atomically(conn: sqlite3.Connection) -> None:
    item = db.add_wishlist_item(conn, WishlistItemIn(name="Draupnir", brand="One Drop"))
    acquired = db.acquire(conn, item.id)
    assert acquired.name == "Draupnir"
    # now in collection, gone from wishlist
    assert len(db.list_collection(conn)) == 1
    assert len(db.list_wishlist(conn)) == 0


def test_acquire_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(db.YoyoNotFound):
        db.acquire(conn, 999)
