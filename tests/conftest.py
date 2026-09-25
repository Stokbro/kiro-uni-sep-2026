"""Shared pytest fixtures."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from yoyo_tracker.core import db


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    """A fresh, isolated in-memory database per test."""
    connection = db.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()
