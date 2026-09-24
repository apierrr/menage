"""Logique métier : lecture des tuiles, validation, annulation, statistiques."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import scheduling
from .clock import to_local
from .clock import today as local_today
from .config import SHARE_WINDOW_DAYS
from .models import (
    KIND_FOLDER,
    KIND_TASK,
    SECTION_ONEOFF,
    SECTION_REGULAR,
    Completion,
    Setting,
    Tile,
    TileCredit,
    TileMember,
    User,
)

_FAR_FUTURE = 10**6

# Les deux tuiles de l'accueil ne sont pas en base : leur couleur, elle, l'est,
# pour que le réglage suive d'un téléphone à l'autre.
DEFAULT_SETTINGS = {"home_regular": "#4f46e5", "home_oneoff": "#0d9488"}


def get_settings(db: Session) -> dict:
    stored = {setting.key: setting.value for setting in db.scalars(select(Setting))}
    return {key: stored.get(key) or default for key, default in DEFAULT_SETTINGS.items()}


def set_settings(db: Session, values: dict) -> dict:
    for key, value in values.items():
        if key in DEFAULT_SETTINGS and value:
            db.merge(Setting(key=key, value=value))
    db.commit()
    return get_settings(db)


# --------------------------------------------------------------------------
# Utilisateurs
# --------------------------------------------------------------------------


def all_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.position, User.id)))


def user_payload(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "name": user.name, "color": user.color, "position": user.position}


def grant_baseline_credits(db: Session, new_user: User) -> None:
    """Met un nouvel arrivant à niveau sur les tâches régulières existantes.

    Sans ça il afficherait zéro validation partout et la rotation par équité lui
    collerait toutes les tâches jusqu'à ce qu'il rattrape les autres.
    """
    others = [u for u in all_users(db) if u.id != new_user.id]
    if not others:
        return

    tiles = db.scalars(
        select(Tile).where(Tile.section == SECTION_REGULAR, Tile.kind == KIND_TASK)
    )
    for tile in tiles:
        # Une tâche réservée à certaines personnes ne concerne pas l'arrivant.
        if explicit_member_ids(db, tile.id):
            continue
        counts = effective_counts(db, tile.id, others)
        baseline = min(counts.values()) if counts else 0
        if baseline > 0:
            db.merge(TileCredit(tile_id=tile.id, user_id=new_user.id, credit=baseline))


# --------------------------------------------------------------------------
# Personnes concernées
# --------------------------------------------------------------------------


def explicit_member_ids(db: Session, tile_id: int) -> list[int]:
    """Personnes cochées sur la tâche ; liste vide = tout le monde."""
    return list(db.scalars(select(TileMember.user_id).where(TileMember.tile_id == tile_id)))


def concerned_users(db: Session, tile: Tile, users: list[User]) -> list[User]:
    """Les profils entre lesquels la tâche tourne, dans l'ordre des profils."""
    ids = set(explicit_member_ids(db, tile.id))
    pool = [user for user in users if user.id in ids]
    # Si toutes les personnes cochées ont été supprimées, la tâche revient à
    # tout le monde plutôt que de rester sans personne.
    return pool or users


def set_members(db: Session, tile: Tile, member_ids: list[int], users: list[User]) -> None:
    """Enregistre les personnes concernées.

    Tout le monde coché revient à ne rien restreindre : un profil ajouté plus
    tard rejoindra la tâche, comme celles qui n'ont jamais été restreintes.
    """
    known = {user.id for user in users}
    wanted = set(member_ids)
    if not wanted <= known:
        raise ValueError("Profil introuvable")

    db.query(TileMember).filter(TileMember.tile_id == tile.id).delete()
    if wanted and wanted != known:
        for user_id in sorted(wanted):
            db.add(TileMember(tile_id=tile.id, user_id=user_id))
    db.flush()


# --------------------------------------------------------------------------
# Compteurs par tuile
# --------------------------------------------------------------------------


def effective_counts(db: Session, tile_id: int, users: list[User]) -> dict[int, int]:
    """Nombre de validations par personne sur cette tuile, crédits inclus."""
    counts = {user.id: 0 for user in users}

    rows = db.execute(
        select(Completion.user_id, func.count(Completion.id))
        .where(Completion.tile_id == tile_id)
        .group_by(Completion.user_id)
    ).all()
    for user_id, count in rows:
        if user_id in counts:
            counts[user_id] += count

    credits = db.execute(
        select(TileCredit.user_id, TileCredit.credit).where(TileCredit.tile_id == tile_id)
    ).all()
    for user_id, credit in credits:
        if user_id in counts:
            counts[user_id] += credit

    return counts


def last_done_map(db: Session, tile_id: int) -> dict[int, dt.datetime]:
    rows = db.execute(
        select(Completion.user_id, func.max(Completion.completed_at))
        .where(Completion.tile_id == tile_id)
        .group_by(Completion.user_id)
    ).all()
    return {user_id: moment for user_id, moment in rows}


# --------------------------------------------------------------------------
# Arborescence
# --------------------------------------------------------------------------


def descendant_task_ids(db: Session, tile_id: int) -> list[int]:
    """Toutes les tâches situées sous un dossier, à n'importe quelle profondeur."""
    task_ids: list[int] = []
    frontier = [tile_id]
    seen = {tile_id}
    while frontier:
        children = db.scalars(select(Tile).where(Tile.parent_id.in_(frontier))).all()
        frontier = []
        for child in children:
            if child.id in seen:
                continue
            seen.add(child.id)
            if child.kind == KIND_TASK:
                task_ids.append(child.id)
            else:
                frontier.append(child.id)
    return task_ids


def breadcrumb(db: Session, tile: Tile | None) -> list[dict]:
    trail: list[dict] = []
    node = tile
    guard = 0
    while node is not None and guard < 50:
        trail.append({"id": node.id, "title": node.title})
        node = db.get(Tile, node.parent_id) if node.parent_id else None
        guard += 1
    return list(reversed(trail))


# --------------------------------------------------------------------------
# Répartition des tâches ponctuelles
# --------------------------------------------------------------------------


def share_for_tiles(db: Session, tile_ids: list[int], users: list[User]) -> dict:
    """% de validations par personne sur une fenêtre glissante."""
    since = local_today() - dt.timedelta(days=SHARE_WINDOW_DAYS)
    counts = {user.id: 0 for user in users}

    if tile_ids:
        rows = db.execute(
            select(Completion.user_id, func.count(Completion.id))
            .where(Completion.tile_id.in_(tile_ids), Completion.completed_on >= since)
            .group_by(Completion.user_id)
        ).all()
        for user_id, count in rows:
            if user_id in counts:
                counts[user_id] = count

    total = sum(counts.values())
    shares = [
        {
            "user_id": user.id,
            "count": counts.get(user.id, 0),
            "pct": round(counts.get(user.id, 0) * 100 / total, 1) if total else 0.0,
        }
        for user in users
    ]
    return {"total": total, "window_days": SHARE_WINDOW_DAYS, "shares": shares}


# --------------------------------------------------------------------------
# Sérialisation
# --------------------------------------------------------------------------


# Couleur d'un sous-menu régulier qui ne contient encore aucune tâche : il n'a
# rien à refléter, donc rien à colorer.
NEUTRAL = "#475569"


def folder_mix(tasks: list[Tile], by_id: dict[int, User], me_id: int | None) -> list[dict]:
    """Répartition des tâches d'un sous-menu régulier, par responsable.

    Un sous-menu n'a pas de couleur à lui : il porte celles des personnes qui
    doivent faire les tâches qu'il contient, au prorata et à n'importe quelle
    profondeur. Trois tâches dont une à moi : un tiers de ma couleur.
    """
    counts: dict[int, int] = defaultdict(int)
    for task in tasks:
        if task.assignee_id in by_id:
            counts[task.assignee_id] += 1

    total = sum(counts.values())
    if not total:
        return []

    # Ma part d'abord, puis la plus grosse : la tuile se lit comme une jauge.
    order = sorted(
        counts,
        key=lambda uid: (0 if uid == me_id else 1, -counts[uid], by_id[uid].position, uid),
    )
    return [
        {
            "user_id": uid,
            "name": by_id[uid].name,
            "color": by_id[uid].color,
            "count": counts[uid],
            "pct": round(counts[uid] * 100 / total, 2),
            "is_me": uid == me_id,
        }
        for uid in order
    ]


def serialize_tile(db: Session, tile: Tile, users: list[User], me_id: int | None) -> dict:
    by_id = {user.id: user for user in users}
    today = local_today()

    data = {
        "id": tile.id,
        "section": tile.section,
        "parent_id": tile.parent_id,
        "kind": tile.kind,
        "title": tile.title,
        "color": tile.color,
        "bullets": tile.bullets,
        "position": tile.position,
    }
    if tile.kind == KIND_TASK:
        # `null` = tout le monde ; sinon les ids des personnes cochées.
        data["members"] = explicit_member_ids(db, tile.id) or None

    if tile.kind == KIND_FOLDER:
        task_ids = descendant_task_ids(db, tile.id)
        if tile.section == SECTION_REGULAR:
            tasks = list(db.scalars(select(Tile).where(Tile.id.in_(task_ids)))) if task_ids else []
            deadlines = [t.due_date for t in tasks if t.due_date is not None]
            mine = [t for t in tasks if me_id is not None and t.assignee_id == me_id]
            soonest = min(deadlines) if deadlines else None
            mix = folder_mix(tasks, by_id, me_id)
            # Pas de couleur choisie : la tuile est faite des couleurs du
            # dessous. `color` reste la teinte dominante, pour tout ce qui ne
            # sait afficher qu'une seule couleur.
            data["color"] = max(mix, key=lambda part: part["count"])["color"] if mix else NEUTRAL
            data["folder"] = {
                "task_count": len(tasks),
                "mine_count": len(mine),
                "is_mine": bool(mine),
                "days_left": (soonest - today).days if soonest else None,
                "is_overdue": bool(soonest and (soonest - today).days < 0),
                "mix": mix,
            }
        else:
            summary = share_for_tiles(db, task_ids, users)
            data["folder"] = {"task_count": len(task_ids), **summary}
        return data

    if tile.section == SECTION_REGULAR:
        days_left = (tile.due_date - today).days if tile.due_date else None
        last_done_on = db.scalar(
            select(func.max(Completion.completed_on)).where(Completion.tile_id == tile.id)
        )
        # La tuile porte la couleur de la personne qui doit la faire : c'est ce
        # qui remplace l'étiquette avec son prénom. Calculé à la lecture, donc
        # la couleur suit la rotation et les changements de profil.
        assignee = by_id.get(tile.assignee_id)
        if assignee is not None:
            data["color"] = assignee.color
        data["regular"] = {
            "due_date": tile.due_date.isoformat() if tile.due_date else None,
            "days_left": days_left,
            "is_overdue": days_left is not None and days_left < 0,
            "is_mine": me_id is not None and tile.assignee_id == me_id,
            "assignee": user_payload(by_id.get(tile.assignee_id)),
            "period_kind": tile.period_kind,
            "period_n": tile.period_n,
            "rotation_mode": tile.rotation_mode,
            # Déjà faite aujourd'hui : l'appui suivant ne changerait rien, la
            # tuile le dit plutôt que de laisser douter.
            "done_today": last_done_on == today,
        }
    else:
        data["oneoff"] = share_for_tiles(db, [tile.id], concerned_users(db, tile, users))

    return data


def sort_key(item: dict) -> tuple:
    """Page Régulier : mes tâches d'abord, puis la plus urgente.

    Ailleurs (Ponctuel, sous-dossiers de ponctuel), l'ordre est celui que
    l'utilisateur a défini au glisser-déposer.
    """
    info = item.get("regular") or item.get("folder") or {}
    is_mine = bool(info.get("is_mine"))
    days_left = info.get("days_left")
    return (
        0 if is_mine else 1,
        days_left if days_left is not None else _FAR_FUTURE,
        item["position"],
        item["id"],
    )


def list_tiles(
    db: Session,
    section: str,
    parent_id: int | None,
    me_id: int | None,
    sort: str = "auto",
) -> list[dict]:
    users = all_users(db)
    query = select(Tile).where(Tile.section == section)
    query = query.where(Tile.parent_id == parent_id) if parent_id else query.where(
        Tile.parent_id.is_(None)
    )
    tiles = list(db.scalars(query.order_by(Tile.position, Tile.id)))

    repaired = False
    for tile in tiles:
        # Un profil supprimé (ou décoché) laisse des tâches orphelines : on
        # réattribue parmi les personnes concernées.
        if tile.section == SECTION_REGULAR and tile.kind == KIND_TASK and users:
            pool = concerned_users(db, tile, users)
            if tile.assignee_id is None or tile.assignee_id not in {u.id for u in pool}:
                tile.assignee_id = scheduling.pick_next_assignee(
                    users=pool,
                    rotation_mode=tile.rotation_mode,
                    counts=effective_counts(db, tile.id, pool),
                    last_done=last_done_map(db, tile.id),
                    just_done_by=None,
                )
                repaired = True
    if repaired:
        db.commit()

    payload = [serialize_tile(db, tile, users, me_id) for tile in tiles]
    # Sur les pages régulières, l'urgence prime par défaut ; `manual` rend la
    # main à l'ordre défini au glisser-déposer.
    if section == SECTION_REGULAR and sort != "manual":
        payload.sort(key=sort_key)
    return payload


# --------------------------------------------------------------------------
# Validation / annulation
# --------------------------------------------------------------------------


def complete_tile(db: Session, tile: Tile, user: User) -> Completion:
    today = local_today()
    users = all_users(db)

    # Si la tuile a déjà été validée aujourd'hui, on recalcule l'échéance à
    # partir de l'état d'avant *cette première validation* : deux personnes qui
    # la valident le même jour arrivent donc exactement à la même date, et le
    # jour de référence mensuel n'est pas redéfini deux fois.
    earlier = first_completion_today(db, tile.id) if tile.section == SECTION_REGULAR else None
    base_due = earlier.prev_due_date if earlier else tile.due_date
    base_anchor = earlier.prev_anchor_day if earlier else tile.anchor_day

    completion = Completion(
        tile_id=tile.id,
        user_id=user.id,
        completed_on=today,
        prev_due_date=tile.due_date,
        prev_assignee_id=tile.assignee_id,
        prev_anchor_day=tile.anchor_day,
    )

    if tile.section == SECTION_REGULAR:
        late_days = scheduling.lateness(base_due, today)
        completion.was_late = late_days > 0
        completion.days_late = late_days

    db.add(completion)
    db.flush()  # la validation doit compter dans la rotation qui suit

    if tile.section == SECTION_REGULAR:
        due, anchor = scheduling.next_due_date(
            tile.period_kind or "week",
            tile.period_n,
            base_anchor,
            base_due,
            today,
        )
        tile.due_date = due
        tile.anchor_day = anchor
        pool = concerned_users(db, tile, users)
        tile.assignee_id = scheduling.pick_next_assignee(
            users=pool,
            rotation_mode=tile.rotation_mode,
            counts=effective_counts(db, tile.id, pool),
            last_done=last_done_map(db, tile.id),
            just_done_by=user.id,
        )

    db.commit()
    return completion


def undo_completion(db: Session, completion: Completion, restore: bool = True) -> None:
    """Supprime une validation.

    `restore` remet l'échéance et le responsable d'avant : ça n'a de sens que
    pour la dernière validation de la tuile.
    """
    tile = db.get(Tile, completion.tile_id)
    if restore and tile is not None and tile.section == SECTION_REGULAR:
        tile.due_date = completion.prev_due_date
        tile.assignee_id = completion.prev_assignee_id
        tile.anchor_day = completion.prev_anchor_day
    db.delete(completion)
    db.commit()


def history_rows(db: Session, limit: int = 200) -> list[dict]:
    """Journal des validations, de la plus récente à la plus ancienne."""
    # La dernière validation de chaque tuile est la seule dont l'annulation
    # peut restaurer proprement l'échéance : on le signale à l'interface.
    latest = {
        tile_id: completion_id
        for tile_id, completion_id in db.execute(
            select(Completion.tile_id, func.max(Completion.id)).group_by(Completion.tile_id)
        ).all()
    }

    rows = db.execute(
        select(Completion, Tile.title, Tile.section, User.name, User.color)
        .join(Tile, Tile.id == Completion.tile_id)
        .join(User, User.id == Completion.user_id)
        .order_by(Completion.id.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": completion.id,
            "tile_id": completion.tile_id,
            "tile_title": title,
            "section": section,
            "user": {"id": completion.user_id, "name": name, "color": color},
            "at": to_local(completion.completed_at).isoformat(timespec="minutes"),
            "on": completion.completed_on.isoformat(),
            "was_late": completion.was_late,
            "days_late": completion.days_late,
            "is_last": latest.get(completion.tile_id) == completion.id,
        }
        for completion, title, section, name, color in rows
    ]


def first_completion_today(db: Session, tile_id: int) -> Completion | None:
    """Première validation du jour sur cette tuile, s'il y en a une."""
    return db.scalars(
        select(Completion)
        .where(Completion.tile_id == tile_id, Completion.completed_on == local_today())
        .order_by(Completion.id)
        .limit(1)
    ).first()


def last_completion(db: Session, tile_id: int) -> Completion | None:
    return db.scalars(
        select(Completion)
        .where(Completion.tile_id == tile_id)
        .order_by(Completion.completed_at.desc(), Completion.id.desc())
        .limit(1)
    ).first()


# --------------------------------------------------------------------------
# Récapitulatif
# --------------------------------------------------------------------------


def build_stats(db: Session, me_id: int | None) -> dict:
    users = all_users(db)
    today = local_today()
    since = today - dt.timedelta(days=SHARE_WINDOW_DAYS)

    regular_tasks = list(
        db.scalars(select(Tile).where(Tile.section == SECTION_REGULAR, Tile.kind == KIND_TASK))
    )
    oneoff_ids = [
        tile.id
        for tile in db.scalars(
            select(Tile).where(Tile.section == SECTION_ONEOFF, Tile.kind == KIND_TASK)
        )
    ]

    done_window = defaultdict(int)
    late_window = defaultdict(int)
    rows = db.execute(
        select(Completion.user_id, Completion.was_late, func.count(Completion.id))
        .where(Completion.completed_on >= since)
        .group_by(Completion.user_id, Completion.was_late)
    ).all()
    for user_id, was_late, count in rows:
        done_window[user_id] += count
        if was_late:
            late_window[user_id] += count

    total_done = sum(done_window.values())
    overdue = [t for t in regular_tasks if t.due_date and (t.due_date - today).days < 0]

    oneoff_done = 0
    if oneoff_ids:
        oneoff_done = (
            db.scalar(
                select(func.count(Completion.id)).where(
                    Completion.completed_on >= since,
                    Completion.tile_id.in_(oneoff_ids),
                )
            )
            or 0
        )

    per_user = []
    for user in users:
        assigned = [t for t in regular_tasks if t.assignee_id == user.id]
        late_for_user = [t for t in assigned if t.due_date and (t.due_date - today).days < 0]
        next_due = min(
            (t.due_date for t in assigned if t.due_date), default=None
        )
        done = done_window.get(user.id, 0)
        per_user.append(
            {
                **user_payload(user),
                "done": done,
                "share_pct": round(done * 100 / total_done, 1) if total_done else 0.0,
                "late_done": late_window.get(user.id, 0),
                "assigned": len(assigned),
                "overdue": len(late_for_user),
                "next_days_left": (next_due - today).days if next_due else None,
                "is_me": user.id == me_id,
            }
        )

    return {
        "window_days": SHARE_WINDOW_DAYS,
        "global": {
            "users": len(users),
            "regular_tasks": len(regular_tasks),
            "oneoff_tasks": len(oneoff_ids),
            "overdue": len(overdue),
            "done": total_done,
            "oneoff_done": oneoff_done,
        },
        "users": per_user,
        "oneoff": share_for_tiles(db, oneoff_ids, users),
    }
