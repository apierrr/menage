from fastapi import APIRouter

from . import core, stats, tiles

api_router = APIRouter()
api_router.include_router(core.router, tags=["core"])
api_router.include_router(tiles.router, prefix="/tiles", tags=["tiles"])
api_router.include_router(tiles.completions_router, prefix="/completions", tags=["tiles"])
api_router.include_router(stats.router, tags=["stats"])

__all__ = ["api_router"]
