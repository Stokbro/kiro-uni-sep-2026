"""Tests for the server-rendered HTML pages."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from yoyo_tracker.api.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("YOYO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(create_app()) as c:
        yield c


def _is_html(resp) -> bool:
    return resp.status_code == 200 and "text/html" in resp.headers["content-type"]


def test_dashboard_renders(client: TestClient) -> None:
    resp = client.get("/")
    assert _is_html(resp)
    assert "Dashboard" in resp.text


def test_collection_page_renders(client: TestClient) -> None:
    assert _is_html(client.get("/collection"))


def test_wishlist_page_renders(client: TestClient) -> None:
    assert _is_html(client.get("/wishlist"))


def test_feed_page_renders(client: TestClient, monkeypatch) -> None:
    from yoyo_tracker.api import pages
    from yoyo_tracker.core.models import RedditPost

    async def fake_fetch(limit: int = 25) -> list[RedditPost]:
        return []

    monkeypatch.setattr(pages.reddit, "fetch_feed", fake_fetch)
    resp = client.get("/feed")
    assert _is_html(resp)
    assert "Community Feed" in resp.text


def test_dashboard_reflects_added_yoyo(client: TestClient) -> None:
    client.post("/api/collection", json={"name": "Shutter", "brand": "YoYoFactory"})
    resp = client.get("/")
    assert "Shutter" in resp.text
    # collection count of 1 shows up on the dashboard
    assert ">1<" in resp.text.replace(" ", "").replace("\n", "")


def test_static_css_served(client: TestClient) -> None:
    resp = client.get("/static/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]
