"""Modèle de données.

Une seule table porte toute la navigation : `tiles`. Une tuile est soit un
dossier (elle ouvre une page contenant d'autres tuiles), soit une tâche. C'est
ce qui rend l'arborescence libre : n'importe quelle tuile peut contenir
n'importe quoi, sur autant de niveaux qu'on veut.
"""

from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    backref,
    mapped_column,
    relationship,
)

from .clock import now_utc
from .constants import (  # noqa: F401  (ré-exportés pour le reste de l'app)
    KIND_FOLDER,
    KIND_TASK,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_WEEK,
    ROTATION_EQUITY,
    ROTATION_ROUND_ROBIN,
    SECTION_ONEOFF,
    SECTION_REGULAR,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    color: Mapped[str] = mapped_column(String(9), default="#6366f1")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)


class Tile(Base):
    __tablename__ = "tiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    section: Mapped[str] = mapped_column(String(16))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tiles.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), default=KIND_TASK)

    title: Mapped[str] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(9), default="#3b82f6")
    body: Mapped[str] = mapped_column(Text, default="[]")  # liste JSON de puces
    position: Mapped[int] = mapped_column(Integer, default=0)

    # --- propre aux tâches régulières ---
    period_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)
    period_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Jour d'ancrage du rythme mensuel. On garde le jour *voulu* (ex. 31) même
    # quand l'échéance a dû être écrêtée à 28/29/30, sinon le rythme dérive.
    anchor_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rotation_mode: Mapped[str] = mapped_column(String(16), default=ROTATION_EQUITY)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)

    # La suppression d'un dossier emporte son contenu (cascade déléguée à
    # SQLite, d'où le PRAGMA foreign_keys=ON à la connexion).
    children: Mapped[list["Tile"]] = relationship(
        "Tile",
        backref=backref("parent", remote_side="Tile.id"),
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def bullets(self) -> list[str]:
        try:
            value = json.loads(self.body or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in value] if isinstance(value, list) else []

    @bullets.setter
    def bullets(self, value: list[str]) -> None:
        self.body = json.dumps([str(v).strip() for v in value if str(v).strip()], ensure_ascii=False)


Index("ix_tiles_nav", Tile.section, Tile.parent_id, Tile.position)


class Completion(Base):
    """Une validation. Conserve l'état d'avant pour permettre l'annulation."""

    __tablename__ = "completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tile_id: Mapped[int] = mapped_column(ForeignKey("tiles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    completed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)
    completed_on: Mapped[dt.date] = mapped_column(Date)  # date locale

    was_late: Mapped[bool] = mapped_column(Boolean, default=False)
    days_late: Mapped[int] = mapped_column(Integer, default=0)

    # État de la tuile juste avant cette validation (pour l'annulation)
    prev_due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    prev_assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_anchor_day: Mapped[int | None] = mapped_column(Integer, nullable=True)


Index("ix_completions_tile", Completion.tile_id, Completion.completed_at)


class TileCredit(Base):
    """Compteur de départ d'une personne sur une tuile.

    Sert aux profils créés après la tuile : sans ça, un nouvel arrivant aurait
    zéro validation partout et hériterait mécaniquement de toutes les tâches en
    mode équité. On le crédite du minimum constaté à son arrivée.
    """

    __tablename__ = "tile_credits"

    tile_id: Mapped[int] = mapped_column(
        ForeignKey("tiles.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    credit: Mapped[int] = mapped_column(Integer, default=0)


class TileMember(Base):
    """Personnes concernées par une tâche.

    Aucune ligne = tout le monde, y compris les profils créés plus tard. Dès
    qu'il y en a, la rotation (et la jauge d'une tâche ponctuelle) se limite à
    ces personnes. Table à part plutôt qu'une colonne : `create_all` la crée
    sur une base existante sans migration.
    """

    __tablename__ = "tile_members"

    tile_id: Mapped[int] = mapped_column(
        ForeignKey("tiles.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
