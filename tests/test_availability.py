"""Tests for store availability — pure parsing plus mocked async transport, no network."""

from __future__ import annotations

import httpx
import pytest

from yoyo_tracker.core import availability
from yoyo_tracker.core.models import AvailabilityStatus, StoreResult

_IN_STOCK_HTML = """
<html><body>
  <li class="product">
    <a href="https://yoyoexpert.com/products/shutter">YoyoFactory Shutter</a>
    <span class="price">$44.99</span>
  </li>
</body></html>
"""

_SOLD_OUT_HTML = """
<html><body>
  <div class="product">
    <a href="/products/chief">CLYW Chief</a>
    <span class="price">$180.00</span>
    <span class="stock">Sold Out</span>
  </div>
</body></html>
"""

_NO_RESULTS_HTML = "<html><body><p>No products found.</p></body></html>"


def test_parse_in_stock() -> None:
    r = availability._parse_yoyoexpert(_IN_STOCK_HTML, "YoyoExpert")
    assert r.status == "in-stock"
    assert r.price == 44.99
    assert r.url == "https://yoyoexpert.com/products/shutter"


def test_parse_sold_out() -> None:
    r = availability._parse_yoyoexpert(_SOLD_OUT_HTML, "YoyoExpert")
    assert r.status == "out-of-stock"
    assert r.price == 180.0


def test_parse_no_results_is_out_of_stock() -> None:
    r = availability._parse_yoyoexpert(_NO_RESULTS_HTML, "YoyoExpert")
    assert r.status == "out-of-stock"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$54.99", 54.99),
        ("54,99", 54.99),
        ("1,299.00", 1299.0),
        ("USD 12", 12.0),
        ("", None),
        (None, None),
        ("free", None),
    ],
)
def test_parse_price(raw: str | None, expected: float | None) -> None:
    assert availability._parse_price(raw) == expected


@pytest.mark.anyio
async def test_check_availability_returns_one_per_store() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_IN_STOCK_HTML)

    transport = httpx.MockTransport(handler)

    # Patch the client construction to use the mock transport.
    orig = httpx.AsyncClient

    def make_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    availability.httpx.AsyncClient = make_client  # type: ignore[assignment]
    try:
        results = await availability.check_availability("Shutter")
    finally:
        availability.httpx.AsyncClient = orig  # type: ignore[assignment]

    assert len(results) == 1
    assert isinstance(results[0], StoreResult)
    assert results[0].store == "YoyoExpert"
    assert results[0].status in ("in-stock", "out-of-stock", "unknown")


@pytest.mark.anyio
async def test_network_failure_degrades_to_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport = httpx.MockTransport(handler)
    orig = httpx.AsyncClient

    def make_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    availability.httpx.AsyncClient = make_client  # type: ignore[assignment]
    try:
        results = await availability.check_availability("anything")
    finally:
        availability.httpx.AsyncClient = orig  # type: ignore[assignment]

    assert results[0].status == "unknown"


def test_status_is_always_valid_literal() -> None:
    valid: set[AvailabilityStatus] = {"in-stock", "out-of-stock", "unknown"}
    for html in (_IN_STOCK_HTML, _SOLD_OUT_HTML, _NO_RESULTS_HTML, "", "<garbage"):
        r = availability._parse_yoyoexpert(html, "YoyoExpert")
        assert r.status in valid
