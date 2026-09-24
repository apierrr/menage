"""Installation, profils, et identité mémorisée."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import colors, service
from ..config import SHARE_WINDOW_DAYS
from ..db import get_db
from ..identity import current_user, forget, remember
from ..models import User
from ..schemas import SessionIn, SettingsPatch, SetupIn, UserIn, UserPatch

router = APIRouter()


def _state(db: Session, me: User | None) -> dict:
    users = service.all_users(db)
    return {
        "setup_done": bool(users),
        "users": [service.user_payload(u) for u in users],
        "me": service.user_payload(me),
        "palette": colors.PALETTE,
        "overdue_color": colors.OVERDUE_COLOR,
        "share_window_days": SHARE_WINDOW_DAYS,
        "settings": service.get_settings(db),
    }


@router.patch("/settings")
def update_settings(payload: SettingsPatch, db: Session = Depends(get_db)):
    return service.set_settings(db, payload.model_dump(exclude_unset=True))


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), me: User | None = Depends(current_user)):
    return _state(db, me)


@router.post("/setup")
def setup(payload: SetupIn, db: Session = Depends(get_db)):
    """Première mise en route : on crée les profils d'un coup."""
    if service.all_users(db):
        raise HTTPException(status_code=409, detail="L'installation a déjà été faite")

    for position, entry in enumerate(payload.users):
        db.add(User(name=entry.name.strip(), color=entry.color, position=position))
    db.commit()
    return _state(db, None)


@router.post("/users", status_code=201)
def create_user(payload: UserIn, db: Session = Depends(get_db)):
    next_position = (db.scalar(select(func.max(User.position))) or -1) + 1
    user = User(name=payload.name.strip(), color=payload.color, position=next_position)
    db.add(user)
    db.commit()

    # Remise à niveau sur les tâches déjà en rotation.
    service.grant_baseline_credits(db, user)
    db.commit()
    return service.user_payload(user)


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserPatch, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profil introuvable")

    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.color is not None:
        user.color = payload.color
    db.commit()
    return service.user_payload(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    response: Response,
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    if len(service.all_users(db)) <= 1:
        raise HTTPException(status_code=409, detail="Il faut au moins un profil")

    db.delete(user)
    db.commit()
    if me is not None and me.id == user_id:
        forget(response)
    return {"ok": True}


@router.post("/session")
def open_session(payload: SessionIn, response: Response, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    remember(response, user.id)
    return service.user_payload(user)


@router.delete("/session")
def close_session(response: Response):
    forget(response)
    return {"ok": True}
