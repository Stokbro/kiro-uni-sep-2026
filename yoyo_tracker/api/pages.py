"""Server-rendered pages (Jinja2). Thin: fetch via core, hand data to templates."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from yoyo_tracker.api.deps import get_conn
from yoyo_tracker.core import db

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

pages = APIRouter(tags=["pages"])


@pages.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> HTMLResponse:
    collection = db.list_collection(conn)
    wishlist = db.list_wishlist(conn)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "collection": collection,
            "wishlist": wishlist,
            "collection_count": len(collection),
            "wishlist_count": len(wishlist),
        },
    )


@pages.get("/collection", response_class=HTMLResponse)
def collection_page(
    request: Request,
    q: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "collection.html",
        {"collection": db.list_collection(conn, q), "q": q},
    )


@pages.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(
    request: Request,
    q: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "wishlist.html",
        {"wishlist": db.list_wishlist(conn, q), "q": q},
    )


@pages.get("/feed", response_class=HTMLResponse)
def feed_page(request: Request, all: bool = False) -> HTMLResponse:
    # The Reddit feed is wired in once core/reddit.py lands; render an empty state
    # for now so the page exists and the nav works.
    return templates.TemplateResponse(
        request,
        "feed.html",
        {"posts": [], "show_all": all, "unavailable": True},
    )
