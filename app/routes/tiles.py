"""CRUD des tuiles, réordonnancement, validation et annulation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import scheduling, service
from ..clock import today as local_today
from ..db import get_db
from ..identity import current_user
from ..models import (
    KIND_FOLDER,
    KIND_TASK,
    PERIOD_WEEK,
    SECTION_REGULAR,
    Completion,
    Tile,
    User,
)
from ..schemas import ReorderIn, TileIn, TilePatch

router = APIRouter()
completions_router = APIRouter()


def _apply_members(db: Session, tile: Tile, member_ids: list[int], users: list[User]) -> None:
    try:
        service.set_members(db, tile, member_ids, users)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _get_tile(db: Session, tile_id: int) -> Tile:
    tile = db.get(Tile, tile_id)
    if tile is None:
        raise HTTPException(status_code=404, detail="Tuile introuvable")
    return tile


@router.get("")
def list_tiles(
    section: str = Query(...),
    parent_id: int | None = Query(default=None),
    sort: str = Query(default="auto", pattern="^(auto|manual)$"),
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    parent = None
    if parent_id is not None:
        parent = _get_tile(db, parent_id)
        if parent.kind != KIND_FOLDER or parent.section != section:
            raise HTTPException(status_code=400, detail="Ce n'est pas un dossier de cette section")

    return {
        "section": section,
        "parent": {"id": parent.id, "title": parent.title, "color": parent.color}
        if parent
        else None,
        "breadcrumb": service.breadcrumb(db, parent),
        "tiles": service.list_tiles(db, section, parent_id, me.id if me else None, sort),
    }


@router.post("", status_code=201)
def create_tile(
    payload: TileIn,
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    if payload.parent_id is not None:
        parent = _get_tile(db, payload.parent_id)
        if parent.kind != KIND_FOLDER or parent.section != payload.section:
            raise HTTPException(status_code=400, detail="Dossier parent invalide")

    query = select(func.max(Tile.position)).where(Tile.section == payload.section)
    query = (
        query.where(Tile.parent_id == payload.parent_id)
        if payload.parent_id is not None
        else query.where(Tile.parent_id.is_(None))
    )
    next_position = (db.scalar(query) or -1) + 1

    tile = Tile(
        section=payload.section,
        parent_id=payload.parent_id,
        kind=payload.kind,
        title=payload.title.strip(),
        color=payload.color,
        position=next_position,
        rotation_mode=payload.rotation_mode,
    )
    tile.bullets = payload.bullets
    users = service.all_users(db)

    if payload.kind == KIND_TASK:
        db.add(tile)
        db.flush()  # il faut l'id pour enregistrer les personnes concernées
        _apply_members(db, tile, payload.member_ids or [], users)

    if payload.section == SECTION_REGULAR and payload.kind == KIND_TASK:
        tile.period_kind = payload.period_kind or PERIOD_WEEK
        tile.period_n = payload.period_n or 1

        if payload.due_date is not None:
            tile.due_date = payload.due_date
            tile.anchor_day = payload.due_date.day
        else:
            due, anchor = scheduling.first_due_date(
                tile.period_kind, tile.period_n, local_today()
            )
            tile.due_date = due
            tile.anchor_day = anchor

        # Qui commence : celui qu'on a choisi, sinon moi, sinon le premier —
        # toujours parmi les personnes concernées.
        pool_ids = [user.id for user in service.concerned_users(db, tile, users)]
        if payload.assignee_id is not None:
            if payload.assignee_id not in pool_ids:
                raise HTTPException(status_code=400, detail="Cette personne n'est pas concernée")
            tile.assignee_id = payload.assignee_id
        elif me is not None and me.id in pool_ids:
            tile.assignee_id = me.id
        elif pool_ids:
            tile.assignee_id = pool_ids[0]

    db.add(tile)
    db.commit()
    return service.serialize_tile(db, tile, service.all_users(db), me.id if me else None)


@router.patch("/{tile_id}")
def update_tile(
    tile_id: int,
    payload: TilePatch,
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    tile = _get_tile(db, tile_id)
    data = payload.model_dump(exclude_unset=True)

    if "title" in data and data["title"]:
        tile.title = data["title"].strip()
    if "color" in data and data["color"]:
        tile.color = data["color"]
    if "bullets" in data and data["bullets"] is not None:
        tile.bullets = data["bullets"]

    users = service.all_users(db)
    if tile.kind == KIND_TASK and data.get("member_ids") is not None:
        _apply_members(db, tile, data["member_ids"], users)

    if tile.section == SECTION_REGULAR and tile.kind == KIND_TASK:
        if data.get("period_kind"):
            tile.period_kind = data["period_kind"]
        if data.get("period_n"):
            tile.period_n = data["period_n"]
        if data.get("rotation_mode"):
            tile.rotation_mode = data["rotation_mode"]
        pool = service.concerned_users(db, tile, users)
        pool_ids = [user.id for user in pool]
        if "assignee_id" in data and data["assignee_id"] is not None:
            if data["assignee_id"] not in pool_ids:
                raise HTTPException(status_code=400, detail="Cette personne n'est pas concernée")
            tile.assignee_id = data["assignee_id"]
        elif tile.assignee_id not in pool_ids and pool:
            # Le responsable vient d'être décoché : la rotation désigne le suivant.
            tile.assignee_id = scheduling.pick_next_assignee(
                users=pool,
                rotation_mode=tile.rotation_mode,
                counts=service.effective_counts(db, tile.id, pool),
                last_done=service.last_done_map(db, tile.id),
                just_done_by=None,
            )
        if "due_date" in data and data["due_date"] is not None:
            tile.due_date = data["due_date"]
            # Changer l'échéance à la main redéfinit le jour de référence mensuel.
            tile.anchor_day = data["due_date"].day

    db.commit()
    return service.serialize_tile(db, tile, users, me.id if me else None)


@router.delete("/{tile_id}")
def delete_tile(tile_id: int, db: Session = Depends(get_db)):
    tile = _get_tile(db, tile_id)
    db.delete(tile)
    db.commit()
    return {"ok": True}


@router.post("/reorder")
def reorder(payload: ReorderIn, db: Session = Depends(get_db)):
    query = select(Tile).where(Tile.section == payload.section)
    query = (
        query.where(Tile.parent_id == payload.parent_id)
        if payload.parent_id is not None
        else query.where(Tile.parent_id.is_(None))
    )
    tiles = {tile.id: tile for tile in db.scalars(query)}

    position = 0
    for tile_id in payload.ids:
        tile = tiles.pop(tile_id, None)
        if tile is None:
            continue
        tile.position = position
        position += 1

    # Les tuiles absentes de la liste (créées entre-temps) restent à la fin.
    for tile in sorted(tiles.values(), key=lambda t: (t.position, t.id)):
        tile.position = position
        position += 1

    db.commit()
    return {"ok": True}


@router.post("/{tile_id}/complete")
def complete(
    tile_id: int,
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    if me is None:
        raise HTTPException(status_code=401, detail="Choisis d'abord ton profil")

    tile = _get_tile(db, tile_id)
    if tile.kind != KIND_TASK:
        raise HTTPException(status_code=400, detail="Un dossier ne se valide pas")

    # Valider veut dire « c'est fait, le compteur repart » : l'échéance ne
    # dépend que du jour de la validation, donc rappuyer ne la déplace pas.
    # Enregistrer une deuxième validation, en revanche, gonflerait les
    # compteurs d'équité et ferait tourner le responsable une fois de trop —
    # on renvoie donc la tuile telle quelle. (Une autre personne qui valide le
    # même jour, elle, l'a bien faite de son côté : ça compte.)
    if tile.section == SECTION_REGULAR:
        previous = service.last_completion(db, tile.id)
        repeat = (
            previous is not None
            and previous.user_id == me.id
            and previous.completed_on == local_today()
        )
        if repeat:
            return {
                "completion_id": previous.id,
                "repeat": True,
                "tile": service.serialize_tile(db, tile, service.all_users(db), me.id),
            }

    completion = service.complete_tile(db, tile, me)
    return {
        "completion_id": completion.id,
        "repeat": False,
        "tile": service.serialize_tile(db, tile, service.all_users(db), me.id),
    }


@completions_router.delete("/{completion_id}")
def undo(
    completion_id: int,
    db: Session = Depends(get_db),
    me: User | None = Depends(current_user),
):
    completion = db.get(Completion, completion_id)
    if completion is None:
        raise HTTPException(status_code=404, detail="Validation introuvable")

    # Seule la dernière validation d'une tuile permet de restaurer l'échéance
    # et le responsable précédents. Une validation plus ancienne se supprime
    # quand même — elle disparaît des compteurs — mais l'échéance en cours,
    # elle, ne se recalcule pas.
    latest = service.last_completion(db, completion.tile_id)
    restores = latest is not None and latest.id == completion.id

    tile_id = completion.tile_id
    service.undo_completion(db, completion, restore=restores)
    tile = db.get(Tile, tile_id)
    return {
        "ok": True,
        "restored": restores,
        "tile": service.serialize_tile(db, tile, service.all_users(db), me.id if me else None)
        if tile
        else None,
    }
