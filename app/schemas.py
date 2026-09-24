"""Contrats d'entrée de l'API."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from . import colors

Section = Literal["regular", "oneoff"]
Kind = Literal["folder", "task"]
PeriodKind = Literal["day", "week", "month"]
RotationMode = Literal["equity", "round_robin"]


def _check_color(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return colors.validate(value)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = "#6366f1"

    @field_validator("color")
    @classmethod
    def _color(cls, value: str) -> str:
        return _check_color(value)


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = None

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _check_color(value)


class SetupIn(BaseModel):
    users: list[UserIn] = Field(min_length=1, max_length=12)


class SessionIn(BaseModel):
    user_id: int


class TileIn(BaseModel):
    section: Section
    parent_id: int | None = None
    kind: Kind = "task"
    title: str = Field(min_length=1, max_length=120)
    color: str = "#3b82f6"
    bullets: list[str] = Field(default_factory=list)

    # Tâches régulières uniquement
    period_kind: PeriodKind | None = None
    period_n: int | None = Field(default=None, ge=1, le=12)
    rotation_mode: RotationMode = "equity"
    assignee_id: int | None = None
    due_date: dt.date | None = None

    # Personnes concernées ; absent ou vide = tout le monde
    member_ids: list[int] | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str) -> str:
        return _check_color(value)


class TilePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = None
    bullets: list[str] | None = None
    period_kind: PeriodKind | None = None
    period_n: int | None = Field(default=None, ge=1, le=12)
    rotation_mode: RotationMode | None = None
    assignee_id: int | None = None
    due_date: dt.date | None = None
    member_ids: list[int] | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _check_color(value)


class SettingsPatch(BaseModel):
    """Couleurs des deux tuiles fixes de l'accueil."""

    home_regular: str | None = None
    home_oneoff: str | None = None

    @field_validator("home_regular", "home_oneoff")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _check_color(value)


class ReorderIn(BaseModel):
    section: Section
    parent_id: int | None = None
    ids: list[int]
