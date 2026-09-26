"""Store availability checks.

External I/O is async (``httpx.AsyncClient``) per the project conventions. Any
network, parse, or store-side failure degrades to an ``unknown`` status rather than
raising — availability is best-effort supplementary data, never a hard dependency of
the core collection features.

Prototype scope: a single store, YoyoExpert. The public surface is stable so more
stores can be added behind :func:`check_availability` without changing callers.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from yoyo_tracker.core.models import StoreResult

_YOYOEXPERT_SEARCH = "https://yoyoexpert.com/search"
_REQUEST_TIMEOUT = 10.0
_USER_AGENT = "yoyo-tracker/0.1 (+https://github.com/; availability check)"


async def check_availability(name: str) -> list[StoreResult]:
    """Check availability of a yoyo by name across all supported stores.

    Returns one :class:`StoreResult` per supported store. A store that cannot be
    reached or parsed yields a result with ``status="unknown"`` rather than being
    omitted, so the caller always sees every store.
    """
    async with httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        return [await _check_yoyoexpert(client, name)]


async def _check_yoyoexpert(client: httpx.AsyncClient, name: str) -> StoreResult:
    """Query YoyoExpert's search page for a yoyo by name.

    Best-effort: any failure returns ``status="unknown"`` for the store.
    """
    store = "YoyoExpert"
    try:
        resp = await client.get(_YOYOEXPERT_SEARCH, params={"q": name})
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.InvalidURL):
        return StoreResult(store=store, status="unknown")

    return _parse_yoyoexpert(resp.text, store)


def _parse_yoyoexpert(html: str, store: str) -> StoreResult:
    """Parse a YoyoExpert search-results page into a :class:`StoreResult`.

    Pure and synchronous so it is unit-testable against saved HTML with no network.
    The heuristics are intentionally forgiving: an unrecognised layout degrades to
    ``unknown`` instead of raising.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:  # noqa: BLE001 — a malformed document must not crash the check
        return StoreResult(store=store, status="unknown")

    product = soup.select_one(".product, .product-item, li.product")
    if product is None:
        # No product card on the results page -> nothing matched.
        return StoreResult(store=store, status="out-of-stock")

    url = _first_href(product)
    price = _first_price(product)
    status = _status_from_card(product)

    return StoreResult(store=store, status=status, price=price, url=url)


def _first_href(product) -> str | None:  # noqa: ANN001 — bs4 Tag, kept loose on purpose
    link = product.select_one("a[href]")
    if link is None:
        return None
    href = link.get("href")
    return href or None


def _first_price(product) -> float | None:  # noqa: ANN001
    price_el = product.select_one(".price, .product-price, [data-price]")
    if price_el is None:
        return None
    raw = price_el.get("data-price") or price_el.get_text(strip=True)
    return _parse_price(raw)


def _parse_price(raw: str | None) -> float | None:
    """Extract a float price from a string like ``"$54.99"`` or ``"54,99 USD"``."""
    if not raw:
        return None
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ".,")
    if not cleaned:
        return None
    # Normalise a comma decimal separator when there is no dot.
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _status_from_card(product) -> str:  # noqa: ANN001
    """Read stock status from a product card, defaulting to ``in-stock``.

    A results card usually means the product exists; an explicit sold-out marker
    flips it to ``out-of-stock``.
    """
    text = product.get_text(" ", strip=True).lower()
    if any(marker in text for marker in ("out of stock", "sold out", "unavailable")):
        return "out-of-stock"
    return "in-stock"
