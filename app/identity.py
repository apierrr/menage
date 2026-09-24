"""Identité mémorisée dans un cookie signé.

Pas d'authentification : l'app est privée, on veut juste éviter de redemander
« qui es-tu ? » à chaque ouverture. Le cookie est signé pour qu'on ne puisse
pas se fabriquer une identité à la main, et dure un an.
"""

from __future__ import annotations

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from .config import SESSION_COOKIE, SESSION_MAX_AGE, get_secret_key
from .db import get_db
from .models import User

_serializer = URLSafeSerializer(get_secret_key(), salt="menage-identity")


def remember(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _serializer.dumps({"uid": user_id}),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def forget(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def read_cookie(request: Request) -> int | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        payload = _serializer.loads(raw)
    except BadSignature:
        return None
    user_id = payload.get("uid") if isinstance(payload, dict) else None
    return int(user_id) if isinstance(user_id, int) else None


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = read_cookie(request)
    return db.get(User, user_id) if user_id else None
