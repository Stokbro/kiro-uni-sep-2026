"""FastAPI application factory.

Thin web layer over ``yoyo_tracker.core``. Wires the database dependency, maps core
domain exceptions to HTTP responses, and mounts the API router.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from yoyo_tracker.api.pages import pages
from yoyo_tracker.api.routes import router
from yoyo_tracker.core import db

STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Yoyo Collection Tracker",
        description="Track your yoyo collection, wishlist, availability, and feed.",
        version="0.1.0",
    )

    @app.exception_handler(db.YoyoNotFound)
    async def _not_found(_: Request, exc: db.YoyoNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(db.DuplicateYoyo)
    async def _conflict(_: Request, exc: db.DuplicateYoyo) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    app.include_router(router)
    app.include_router(pages)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app


app = create_app()


def run() -> None:
    """Console-script entrypoint: serve the app with uvicorn."""
    import uvicorn

    uvicorn.run("yoyo_tracker.api.app:app", host="127.0.0.1", port=8000, reload=False)
