"""Integration tests for the FastAPI layer using TestClient.

Each test gets an isolated on-disk temp database via the ``YOYO_DB_PATH`` env var,
set through pytest's ``tmp_path`` fixture.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from yoyo_tracker.api.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("YOYO_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_collection_starts_empty(client: TestClient) -> None:
    resp = client.get("/api/collection")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_and_list_collection(client: TestClient) -> None:
    resp = client.post(
        "/api/collection", json={"name": "Shutter", "brand": "YoYoFactory"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Shutter"
    assert body["condition"] == "good"
    assert body["id"] > 0

    listing = client.get("/api/collection").json()
    assert len(listing) == 1


def test_add_invalid_yoyo_returns_422(client: TestClient) -> None:
    resp = client.post("/api/collection", json={"name": "", "brand": "X"})
    assert resp.status_code == 422


def test_delete_collection_item(client: TestClient) -> None:
    created = client.post(
        "/api/collection", json={"name": "Shutter", "brand": "YoYoFactory"}
    ).json()
    resp = client.delete(f"/api/collection/{created['id']}")
    assert resp.status_code == 204
    assert client.get("/api/collection").json() == []


def test_delete_missing_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/collection/999")
    assert resp.status_code == 404


def test_search_collection(client: TestClient) -> None:
    client.post("/api/collection", json={"name": "Shutter", "brand": "YoYoFactory"})
    client.post("/api/collection", json={"name": "Draupnir", "brand": "One Drop"})
    resp = client.get("/api/collection", params={"q": "shut"})
    assert len(resp.json()) == 1


def test_wishlist_flow(client: TestClient) -> None:
    resp = client.post(
        "/api/wishlist", json={"name": "Draupnir", "brand": "One Drop", "max_price": 180}
    )
    assert resp.status_code == 201
    assert len(client.get("/api/wishlist").json()) == 1


def test_cannot_wishlist_owned_item_returns_409(client: TestClient) -> None:
    client.post("/api/collection", json={"name": "Shutter", "brand": "YoYoFactory"})
    resp = client.post(
        "/api/wishlist", json={"name": "Shutter", "brand": "YoYoFactory"}
    )
    assert resp.status_code == 409


def test_acquire_moves_item(client: TestClient) -> None:
    item = client.post(
        "/api/wishlist", json={"name": "Draupnir", "brand": "One Drop"}
    ).json()
    resp = client.post(f"/api/wishlist/{item['id']}/acquire")
    assert resp.status_code == 201
    assert resp.json()["name"] == "Draupnir"
    assert client.get("/api/wishlist").json() == []
    assert len(client.get("/api/collection").json()) == 1


def test_acquire_missing_returns_404(client: TestClient) -> None:
    resp = client.post("/api/wishlist/999/acquire")
    assert resp.status_code == 404
