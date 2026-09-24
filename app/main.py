"""Point d'entrée : API sous /api, front statique pour tout le reste."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .db import init_db
from .routes import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Ménage", docs_url=None, redoc_url=None, lifespan=lifespan)
app.include_router(api_router, prefix="/api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str):
    """Sert les fichiers du build, et l'index pour toutes les routes du front."""
    root = STATIC_DIR.resolve()
    if full_path:
        candidate = (root / full_path).resolve()
        if root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)

    index = root / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Front non construit"}, status_code=503)
