"""Reddit community feed.

Read-only, credential-free access via Reddit's public ``.json`` endpoints (per the
product requirements). External I/O is async; any failure degrades to an empty feed
rather than raising, so a Reddit outage never breaks the app.

The filtering step (:func:`filter_posts`) is pure and synchronous so it is unit-testable
without network access.
"""

from __future__ import annotations

import httpx

from yoyo_tracker.core.models import RedditPost

_SUBREDDITS = ("Throwers", "Yoyo")
_REQUEST_TIMEOUT = 10.0
_DEFAULT_LIMIT = 25
_USER_AGENT = "yoyo-tracker/0.1 (+https://github.com/; community feed)"


async def fetch_feed(limit: int = _DEFAULT_LIMIT) -> list[RedditPost]:
    """Fetch recent posts from the supported subreddits.

    Returns posts across all subreddits, newest-first per subreddit. A subreddit that
    cannot be reached or parsed contributes nothing rather than failing the whole feed.
    """
    posts: list[RedditPost] = []
    async with httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        for sub in _SUBREDDITS:
            posts.extend(await _fetch_subreddit(client, sub, limit))
    return posts


async def _fetch_subreddit(
    client: httpx.AsyncClient, subreddit: str, limit: int
) -> list[RedditPost]:
    """Fetch one subreddit's recent posts. Best-effort: failures return ``[]``."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    try:
        resp = await client.get(url, params={"limit": limit})
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    return _parse_listing(payload, subreddit)


def _parse_listing(payload: object, subreddit: str) -> list[RedditPost]:
    """Parse a Reddit listing JSON payload into :class:`RedditPost` objects.

    Pure and defensive: an unexpected shape yields ``[]`` instead of raising.
    """
    if not isinstance(payload, dict):
        return []
    children = payload.get("data", {}).get("children", [])
    if not isinstance(children, list):
        return []

    posts: list[RedditPost] = []
    for child in children:
        data = child.get("data", {}) if isinstance(child, dict) else {}
        title = data.get("title")
        permalink = data.get("permalink")
        if not title or not permalink:
            continue
        posts.append(
            RedditPost(
                title=title,
                url=f"https://www.reddit.com{permalink}",
                subreddit=data.get("subreddit", subreddit),
                score=int(data.get("score", 0) or 0),
                author=data.get("author"),
            )
        )
    return posts


def filter_posts(posts: list[RedditPost], names: list[str]) -> list[RedditPost]:
    """Return only posts whose title mentions one of ``names`` (case-insensitive).

    An empty ``names`` list yields an empty result — there is nothing to match against,
    which is the correct "filtered view with no tracked yoyos" behaviour. Callers that
    want everything should use the unfiltered list directly.
    """
    needles = [n.strip().lower() for n in names if n and n.strip()]
    if not needles:
        return []
    out: list[RedditPost] = []
    for post in posts:
        title = post.title.lower()
        if any(needle in title for needle in needles):
            out.append(post)
    return out
