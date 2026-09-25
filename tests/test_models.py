"""Example-based tests for the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from yoyo_tracker.core.models import StoreResult, WishlistItemIn, YoyoIn


def test_yoyo_defaults() -> None:
    y = YoyoIn(name="Shutter", brand="YoYoFactory")
    assert y.condition == "good"
    assert y.colorway is None
    assert y.notes is None


def test_yoyo_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        YoyoIn(name="", brand="YoYoFactory")


def test_yoyo_rejects_bad_condition() -> None:
    with pytest.raises(ValidationError):
        YoyoIn(name="Shutter", brand="YoYoFactory", condition="scratched")


def test_wishlist_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        WishlistItemIn(name="Draupnir", brand="One Drop", max_price=-5)


def test_wishlist_allows_none_price() -> None:
    item = WishlistItemIn(name="Draupnir", brand="One Drop")
    assert item.max_price is None


def test_store_result_status_literal() -> None:
    ok = StoreResult(store="YoyoExpert", status="in-stock", price=54.99)
    assert ok.status == "in-stock"
    with pytest.raises(ValidationError):
        StoreResult(store="YoyoExpert", status="maybe")
