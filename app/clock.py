"""Le temps, vu depuis Paris.

Toute la logique de décompte raisonne en **jours pleins locaux** : un compteur
perd un jour au passage de minuit heure de Paris, pas 24 h après la validation.
Les horodatages sont stockés en UTC naïf ; seules les dates (échéances,
validations) sont des dates locales.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .config import TIMEZONE

LOCAL_TZ = ZoneInfo(TIMEZONE)


def now_utc() -> dt.datetime:
    """Instant courant, en UTC naïf (format de stockage)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def today() -> dt.date:
    """Date du jour, heure locale."""
    return dt.datetime.now(LOCAL_TZ).date()


def to_local(naive_utc: dt.datetime) -> dt.datetime:
    """Repasse un horodatage stocké en UTC naïf vers l'heure locale."""
    return naive_utc.replace(tzinfo=dt.timezone.utc).astimezone(LOCAL_TZ)


def local_date_of(naive_utc: dt.datetime) -> dt.date:
    return to_local(naive_utc).date()


def days_between(start: dt.date, end: dt.date) -> int:
    """Nombre de jours pleins entre deux dates (négatif si `end` est passée)."""
    return (end - start).days
