"""Moteur de planification et de rotation.

Fonctions pures, sans base de données : c'est ici que vivent les deux règles
qui font tourner les tâches régulières.

1. Échéance — *une validation remet le compteur à zéro*. La prochaine échéance
   tombe une période entière après le jour où la tâche a été faite, qu'on soit
   en avance, à l'heure ou en retard : « c'est fait, il faudra la refaire dans
   sept jours ». Le compteur ne dépend donc que de la dernière validation, ce
   qui rend l'opération idempotente — rappuyer ne peut pas repousser l'échéance
   une deuxième fois.

2. Rythme mensuel — on mémorise le jour *voulu* (l'ancrage). Une tâche calée
   sur le 31 tombe le 28 février puis revient au 31 mars ; si on ne gardait
   que la dernière date, elle resterait bloquée au 28.
"""

from __future__ import annotations

import calendar
import datetime as dt

from .constants import PERIOD_DAY, PERIOD_MONTH, PERIOD_WEEK, ROTATION_ROUND_ROBIN

_FAR_PAST = dt.datetime.min


def clamp_to_month(year: int, month: int, day: int) -> dt.date:
    """Ramène un jour d'ancrage au dernier jour du mois s'il n'existe pas."""
    last_day = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day, last_day))


def add_months(base: dt.date, months: int, anchor_day: int) -> dt.date:
    index = base.month - 1 + months
    year = base.year + index // 12
    month = index % 12 + 1
    return clamp_to_month(year, month, anchor_day)


def add_period(
    base: dt.date, period_kind: str, period_n: int | None, anchor_day: int | None
) -> dt.date:
    steps = max(1, period_n or 1)
    if period_kind == PERIOD_DAY:
        return base + dt.timedelta(days=steps)
    if period_kind == PERIOD_WEEK:
        return base + dt.timedelta(days=7 * steps)
    return add_months(base, steps, anchor_day or base.day)


def first_due_date(
    period_kind: str, period_n: int | None, start: dt.date
) -> tuple[dt.date, int | None]:
    """Première échéance d'une tâche qu'on vient de créer.

    Une tâche quotidienne est à faire dès aujourd'hui ; les autres laissent
    une période entière avant la première fois.
    """
    if period_kind == PERIOD_DAY:
        return start, None
    anchor = start.day if period_kind == PERIOD_MONTH else None
    return add_period(start, period_kind, period_n, anchor), anchor


def next_due_date(
    period_kind: str,
    period_n: int | None,
    anchor_day: int | None,
    prev_due: dt.date | None,
    done_on: dt.date,
) -> tuple[dt.date, int | None]:
    """Échéance suivante après une validation.

    Le compteur repart de zéro : on compte une période entière depuis le jour
    de la validation, jamais depuis l'échéance précédente. Deux conséquences
    voulues — celui qui traîne ne rogne pas le délai du suivant, et valider
    deux fois le même jour donne exactement la même échéance.

    Renvoie le couple (nouvelle échéance, nouvel ancrage).
    """
    anchor = anchor_day
    if period_kind == PERIOD_MONTH and (anchor is None or done_on != prev_due):
        # Faite un autre jour que celui prévu : ce jour-là devient la nouvelle
        # référence. Faite pile à l'échéance, on conserve l'ancrage — c'est ce
        # qui ramène au 31 mars une tâche que février avait poussée au 28.
        anchor = done_on.day

    return add_period(done_on, period_kind, period_n, anchor), anchor


def lateness(prev_due: dt.date | None, done_on: dt.date) -> int:
    """Nombre de jours de retard (0 si à l'heure ou en avance)."""
    if prev_due is None:
        return 0
    return max(0, (done_on - prev_due).days)


def pick_next_assignee(
    *,
    users: list,
    rotation_mode: str,
    counts: dict[int, int],
    last_done: dict[int, dt.datetime | None],
    just_done_by: int | None,
) -> int | None:
    """Qui doit faire la tâche la prochaine fois.

    - `round_robin` : la personne suivante dans l'ordre des profils, à partir de
      celle qui vient de valider.
    - `equity` (défaut) : celle qui a fait cette tâche le moins souvent ;
      à égalité, celle qui l'a faite il y a le plus longtemps (jamais = en
      premier), puis l'ordre des profils.
    """
    if not users:
        return None

    ordered = sorted(users, key=lambda u: (u.position, u.id))

    if rotation_mode == ROTATION_ROUND_ROBIN:
        ids = [u.id for u in ordered]
        if just_done_by in ids:
            return ids[(ids.index(just_done_by) + 1) % len(ids)]
        return ids[0]

    def rank(user):
        return (
            counts.get(user.id, 0),
            last_done.get(user.id) or _FAR_PAST,
            user.position,
            user.id,
        )

    return min(ordered, key=rank).id
