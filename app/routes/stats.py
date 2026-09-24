"""Page récapitulative : indicateurs globaux et par personne."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import service
from ..db import get_db
from ..identity import current_user
from ..models import User

router = APIRouter()


@router.get("/stats")
def stats(db: Session = Depends(get_db), me: User | None = Depends(current_user)):
    return service.build_stats(db, me.id if me else None)


@router.get("/history")
def history(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Journal des validations, pour relire et corriger ce qui a été coché."""
    return {"entries": service.history_rows(db, limit)}
