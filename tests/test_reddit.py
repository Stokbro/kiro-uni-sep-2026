"""Tests for the Reddit feed — pure parse/filter plus mocked transport, no network."""

from __future__ import annotations

import httpx
import pytest

from yoyo_tracker.core import reddit
from yoyo_tracker.core.models import RedditPost


def _listing(*titles: str) -> dict:
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "title": t,
                        "permalink": f"/r/Throwers/comments/{i}/",
                        "subreddit": "Throwers",
                        "score": i * 10,
                        "author": f"user{i}",
                    }
                }
                for i, t in enumerate(titles)
            ]
        }
    }


def test_parse_listing() -> None:
    posts = reddit._parse_listing(_listing("Shutter review", "CLYW drop"), "Throwers")
    assert len(posts) == 2
    assert posts[0].title == "Shutter review"
    assert posts[0].url.startswith("https://www.reddit.com/r/Throwers/comments/")
    assert posts[1].score == 10


def test_parse_listing_skips_incomplete() -> None:
    payload = {"data": {"children": [{"data": {"title": "no permalink"}}]}}
    assert reddit._parse_listing(payload, "Yoyo") == []


def test_parse_listing_bad_shape_returns_empty() -> None:
    assert reddit._parse_listing("not a dict", "Yoyo") == []
    assert reddit._parse_listing({}, "Yoyo") == []
    assert reddit._parse_listing({"data": {"children": "nope"}}, "Yoyo") == []


def test_filter_posts_matches_names_case_insensitive() -> None:
    posts = [
        RedditPost(title="New SHUTTER colorway", url="u1", subreddit="Throwers"),
        RedditPost(title="One Drop restock", url="u2", subreddit="Yoyo"),
        RedditPost(title="Random meta chat", url="u3", subreddit="Throwers"),
    ]
    out = reddit.filter_posts(posts, ["shutter", "One Drop Top Deck"])
    titles = {p.title for p in out}
    assert "New SHUTTER colorway" in titles
    assert "Random meta chat" not in titles


def test_filter_posts_empty_names_returns_empty() -> None:
    posts = [RedditPost(title="anything", url="u", subreddit="Yoyo")]
    assert reddit.filter_posts(posts, []) == []
    assert reddit.filter_posts(posts, ["  ", ""]) == []


@pytest.mark.anyio
async def test_fetch_feed_aggregates_subreddits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_listing("post A", "post B"))

    transport = httpx.MockTransport(handler)
    orig = httpx.AsyncClient

    def make_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    reddit.httpx.AsyncClient = make_client  # type: ignore[assignment]
    try:
        posts = await reddit.fetch_feed(limit=5)
    finally:
        reddit.httpx.AsyncClient = orig  # type: ignore[assignment]

    # Two subreddits x two posts each.
    assert len(posts) == 4
    assert all(isinstance(p, RedditPost) for p in posts)


@pytest.mark.anyio
async def test_fetch_feed_network_failure_is_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport = httpx.MockTransport(handler)
    orig = httpx.AsyncClient

    def make_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    reddit.httpx.AsyncClient = make_client  # type: ignore[assignment]
    try:
        posts = await reddit.fetch_feed()
    finally:
        reddit.httpx.AsyncClient = orig  # type: ignore[assignment]

    assert posts == []
