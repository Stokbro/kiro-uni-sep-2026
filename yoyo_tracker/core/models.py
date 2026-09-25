"""Data models and shared types for the yoyo tracker.

Pydantic models are the single source of truth for data shapes and invariants.
Allowed enumerated values are expressed as ``Literal`` types so validation and the
type checker agree.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Condition = Literal["mint", "good", "played"]
AvailabilityStatus = Literal["in-stock", "out-of-stock", "unknown"]


class YoyoIn(BaseModel):
    """Input model for adding a yoyo to the collection."""

    name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    colorway: str | None = None
    condition: Condition = "good"
    date_acquired: str | None = None
    notes: str | None = None


class YoyoOut(YoyoIn):
    """A yoyo as stored, including its database id and creation timestamp."""

    id: int
    created_at: str


class WishlistItemIn(BaseModel):
    """Input model for adding a yoyo to the wishlist."""

    name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    max_price: float | None = Field(default=None, ge=0)
    notes: str | None = None


class WishlistItemOut(WishlistItemIn):
    """A wishlist item as stored, including its database id and creation timestamp."""

    id: int
    created_at: str


class StoreResult(BaseModel):
    """Availability of a yoyo at a single store."""

    store: str
    status: AvailabilityStatus
    price: float | None = None
    url: str | None = None


class RedditPost(BaseModel):
    """A single Reddit post from the community feed."""

    title: str
    url: str
    subreddit: str
    score: int = 0
    author: str | None = None
