"""Property-based tests for the core invariants (Lesson 4 / hypothesis).

Example-based tests check specific cases; these enforce the *general rules* from the
spec's Invariants section against many generated inputs. Every test drives the pure
``core`` layer against a fresh in-memory database — no API, no network.

Invariants covered (spec §Invariants):
  1. A collection name is never simultaneously in the wishlist.
  2. list_collection returns exactly the surviving set after a series of add/remove.
  3. Availability status is always one of the AvailabilityStatus literals.
  4. acquire moves a yoyo from wishlist to collection atomically (both or neither).
  5. Empty-query search returns everything; a name query returns only matches.
  6. Round-trip: a yoyo added then read back has identical field values.
  7. Adding a name already on the wishlist is rejected (DuplicateYoyo), and vice versa.
"""

from __future__ import annotations

import sqlite3

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from yoyo_tracker.core import availability, db
from yoyo_tracker.core.models import (
    AvailabilityStatus,
    Condition,
    WishlistItemIn,
    YoyoIn,
)

# Names/brands: non-empty, no leading/trailing whitespace surprises, printable.
_text = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=40,
)
_conditions: list[Condition] = ["mint", "good", "played"]
_valid_status: set[AvailabilityStatus] = {"in-stock", "out-of-stock", "unknown"}

# hypothesis + a function-scoped fixture: the fixture is created once per test, and
# @given re-runs the body many times against that same fresh DB. We reset the DB at
# the top of each example instead, so examples don't leak into each other.
_SUPPRESS = [HealthCheck.function_scoped_fixture]


def _reset(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM collection")
    conn.execute("DELETE FROM wishlist")
    conn.commit()


@settings(max_examples=100, suppress_health_check=_SUPPRESS)
@given(name=_text, brand=_text, cond=st.sampled_from(_conditions))
def test_roundtrip_preserves_fields(
    conn: sqlite3.Connection, name: str, brand: str, cond: Condition
) -> None:
    """Invariant 6: a yoyo added then read back has identical field values."""
    _reset(conn)
    created = db.add_yoyo(conn, YoyoIn(name=name, brand=brand, condition=cond))
    fetched = db.get_yoyo(conn, created.id)
    assert fetched.name == name
    assert fetched.brand == brand
    assert fetched.condition == cond


@settings(max_examples=100, suppress_health_check=_SUPPRESS)
@given(name=_text, brand=_text)
def test_collection_and_wishlist_mutually_exclusive(
    conn: sqlite3.Connection, name: str, brand: str
) -> None:
    """Invariant 1 + 7: the same name cannot live in both tables."""
    _reset(conn)
    db.add_yoyo(conn, YoyoIn(name=name, brand=brand))
    # Same name onto the wishlist must be rejected.
    with pytest.raises(db.DuplicateYoyo):
        db.add_wishlist_item(conn, WishlistItemIn(name=name, brand=brand))

    _reset(conn)
    db.add_wishlist_item(conn, WishlistItemIn(name=name, brand=brand))
    # And the reverse direction.
    with pytest.raises(db.DuplicateYoyo):
        db.add_yoyo(conn, YoyoIn(name=name, brand=brand))


@settings(max_examples=60, suppress_health_check=_SUPPRESS)
@given(
    names=st.lists(_text, min_size=1, max_size=8, unique=True),
    brand=_text,
    remove_frac=st.floats(min_value=0.0, max_value=1.0),
)
def test_list_reflects_surviving_set(
    conn: sqlite3.Connection, names: list[str], brand: str, remove_frac: float
) -> None:
    """Invariant 2: list_collection returns exactly what was added minus removed."""
    _reset(conn)
    created = [db.add_yoyo(conn, YoyoIn(name=n, brand=brand)) for n in names]

    cut = int(len(created) * remove_frac)
    to_remove = created[:cut]
    for y in to_remove:
        db.remove_yoyo(conn, y.id)

    survivors = {y.id for y in created[cut:]}
    listed = {y.id for y in db.list_collection(conn)}
    assert listed == survivors


@settings(max_examples=80, suppress_health_check=_SUPPRESS)
@given(
    names=st.lists(_text, min_size=1, max_size=6, unique=True),
    needle=_text,
    brand=_text,
)
def test_search_semantics(
    conn: sqlite3.Connection, names: list[str], needle: str, brand: str
) -> None:
    """Invariant 5: empty query returns all; a query returns only matching items."""
    _reset(conn)
    for n in names:
        db.add_yoyo(conn, YoyoIn(name=n, brand=brand))

    # Empty query -> everything.
    assert len(db.list_collection(conn, "")) == len(names)

    # A query -> a subset, and every result actually matches (name or brand).
    results = db.list_collection(conn, needle)
    low = needle.lower()
    assert len(results) <= len(names)
    for r in results:
        assert low in r.name.lower() or low in r.brand.lower()


@settings(max_examples=80, suppress_health_check=_SUPPRESS)
@given(name=_text, brand=_text, cond=st.sampled_from(_conditions))
def test_acquire_is_atomic_move(
    conn: sqlite3.Connection, name: str, brand: str, cond: Condition
) -> None:
    """Invariant 4: acquire removes from wishlist AND adds to collection."""
    _reset(conn)
    item = db.add_wishlist_item(conn, WishlistItemIn(name=name, brand=brand))
    acquired = db.acquire(conn, item.id, condition=cond)

    coll_names = {y.name for y in db.list_collection(conn)}
    wish_names = {w.name for w in db.list_wishlist(conn)}
    assert name in coll_names  # added to collection
    assert name not in wish_names  # removed from wishlist
    assert acquired.condition == cond
    # And it did not leave a dangling wishlist row.
    with pytest.raises(db.YoyoNotFound):
        db.get_wishlist_item(conn, item.id)


@settings(max_examples=200)
@given(html=st.text(max_size=2000))
def test_availability_status_always_valid(html: str) -> None:
    """Invariant 3: parsed availability status is always a valid literal.

    Feeds arbitrary text into the YoyoExpert parser — it must never produce a status
    outside the allowed set, and never raise.
    """
    result = availability._parse_yoyoexpert(html, "YoyoExpert")
    assert result.status in _valid_status
    assert result.store == "YoyoExpert"
