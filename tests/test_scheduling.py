"""Tests du moteur de dates et de rotation.

Sans dépendance : `python3 -m tests.test_scheduling` depuis la racine du projet.
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import scheduling  # noqa: E402
from app.constants import PERIOD_DAY, PERIOD_MONTH, PERIOD_WEEK  # noqa: E402

D = dt.date
checks = 0


def check(actual, expected, label: str) -> None:
    global checks
    assert actual == expected, f"{label} : attendu {expected}, obtenu {actual}"
    checks += 1


# --- Rythme quotidien -------------------------------------------------------

due, anchor = scheduling.first_due_date(PERIOD_DAY, 1, D(2026, 7, 15))
check((due, anchor), (D(2026, 7, 15), None), "quotidien : à faire dès le jour de création")

due, _ = scheduling.next_due_date(PERIOD_DAY, 1, None, D(2026, 7, 15), D(2026, 7, 15))
check(due, D(2026, 7, 16), "quotidien, faite le jour même : demain")

due, _ = scheduling.next_due_date(PERIOD_DAY, 1, None, D(2026, 7, 15), D(2026, 7, 18))
check(due, D(2026, 7, 19), "quotidien, faite en retard : le lendemain de la validation")

due, _ = scheduling.next_due_date(PERIOD_DAY, 1, None, D(2026, 2, 28), D(2026, 2, 28))
check(due, D(2026, 3, 1), "quotidien, passage de mois")


# --- Rythme hebdomadaire ----------------------------------------------------

# Faite le jour prévu : le rythme se cale sur ce jour-là.
due, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, D(2026, 7, 15), D(2026, 7, 15))
check(due, D(2026, 7, 22), "hebdo, faite à l'heure")

# En avance : le compteur repart de la validation, pas de l'échéance prévue.
due, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, D(2026, 7, 15), D(2026, 7, 13))
check(due, D(2026, 7, 20), "hebdo, faite en avance")

# En retard : on repart de la validation, le suivant récupère un délai entier.
due, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, D(2026, 7, 15), D(2026, 7, 18))
check(due, D(2026, 7, 25), "hebdo, faite en retard")

# Le compteur ne dépend que du jour de la validation : rappuyer ne repousse
# rien. C'est la règle qui empêche « 3 clics = 21 jours ».
first, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, D(2026, 7, 15), D(2026, 7, 15))
second, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, first, D(2026, 7, 15))
third, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, second, D(2026, 7, 15))
check((second, third), (first, first), "trois validations le même jour, une seule échéance")

# Peu importe d'où l'on vient : seule la date de validation compte.
from_far, _ = scheduling.next_due_date(PERIOD_WEEK, 1, None, D(2026, 9, 30), D(2026, 7, 15))
check(from_far, D(2026, 7, 22), "l'échéance précédente n'entre pas dans le calcul")

# Deux et trois semaines.
due, _ = scheduling.next_due_date(PERIOD_WEEK, 2, None, D(2026, 7, 15), D(2026, 7, 15))
check(due, D(2026, 7, 29), "2 semaines")
due, _ = scheduling.next_due_date(PERIOD_WEEK, 3, None, D(2026, 7, 15), D(2026, 7, 15))
check(due, D(2026, 8, 5), "3 semaines")

# Le jour de la semaine est conservé de bout en bout.
cursor, anchor = D(2026, 1, 7), None  # un mercredi
for _ in range(30):
    cursor, anchor = scheduling.next_due_date(PERIOD_WEEK, 1, anchor, cursor, cursor)
check(cursor.weekday(), 2, "hebdo, toujours un mercredi après 30 cycles")

# --- Rythme mensuel : le 31 doit revenir au 31 ------------------------------

due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, 31, D(2026, 1, 31), D(2026, 1, 31))
check(due, D(2026, 2, 28), "31 janvier → février non bissextile")
check(anchor, 31, "l'ancrage reste le 31")

due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, anchor, due, due)
check(due, D(2026, 3, 31), "février → 31 mars (l'ancrage n'est pas perdu)")

due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, anchor, due, due)
check(due, D(2026, 4, 30), "31 mars → 30 avril (avril n'a que 30 jours)")

due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, anchor, due, due)
check(due, D(2026, 5, 31), "30 avril → 31 mai")

# Année bissextile.
due, _ = scheduling.next_due_date(PERIOD_MONTH, 1, 31, D(2028, 1, 31), D(2028, 1, 31))
check(due, D(2028, 2, 29), "31 janvier 2028 → 29 février (bissextile)")

# Passage d'année.
due, _ = scheduling.next_due_date(PERIOD_MONTH, 1, 31, D(2026, 12, 31), D(2026, 12, 31))
check(due, D(2027, 1, 31), "31 décembre → 31 janvier")

# Le 29 février existe : l'ancrage 29 retombe sur 28 les années normales.
due, anchor = scheduling.next_due_date(PERIOD_MONTH, 12, 29, D(2028, 2, 29), D(2028, 2, 29))
check(due, D(2029, 2, 28), "29 février + 12 mois → 28 février")

# Mensuel en retard : le jour de référence devient celui de la validation.
due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, 5, D(2026, 3, 5), D(2026, 3, 9))
check(due, D(2026, 4, 9), "mensuel en retard → nouveau jour de référence")
check(anchor, 9, "l'ancrage suit la validation en retard")

# Mensuel en avance : le compteur repart du jour de la validation, qui devient
# donc le nouveau jour de référence.
due, anchor = scheduling.next_due_date(PERIOD_MONTH, 1, 31, D(2026, 2, 28), D(2026, 2, 20))
check(due, D(2026, 3, 20), "mensuel en avance → un mois plein depuis la validation")
check(anchor, 20, "l'ancrage suit la validation en avance")

# --- Première échéance ------------------------------------------------------

due, anchor = scheduling.first_due_date(PERIOD_WEEK, 1, D(2026, 7, 26))
check(due, D(2026, 8, 2), "première échéance hebdo")
check(anchor, None, "pas d'ancrage pour l'hebdo")

due, anchor = scheduling.first_due_date(PERIOD_MONTH, 1, D(2026, 1, 31))
check((due, anchor), (D(2026, 2, 28), 31), "première échéance mensuelle depuis un 31")

# --- Retard -----------------------------------------------------------------

check(scheduling.lateness(D(2026, 7, 15), D(2026, 7, 18)), 3, "3 jours de retard")
check(scheduling.lateness(D(2026, 7, 15), D(2026, 7, 12)), 0, "en avance = 0 jour de retard")
check(scheduling.lateness(None, D(2026, 7, 12)), 0, "sans échéance = 0")


# --- Rotation ---------------------------------------------------------------


@dataclass
class FakeUser:
    id: int
    position: int


alice, bob, chloe = FakeUser(1, 0), FakeUser(2, 1), FakeUser(3, 2)
trio = [alice, bob, chloe]


def rotate(mode, counts, last=None, just_done_by=None):
    return scheduling.pick_next_assignee(
        users=trio,
        rotation_mode=mode,
        counts=counts,
        last_done=last or {},
        just_done_by=just_done_by,
    )


# Chacun son tour : on suit l'ordre des profils depuis celui qui vient de faire.
check(rotate("round_robin", {}, just_done_by=1), 2, "chacun son tour : après Alice, Bob")
check(rotate("round_robin", {}, just_done_by=3), 1, "chacun son tour : après Chloé, Alice")

# Équité : celui qui a le moins fait cette tâche.
check(rotate("equity", {1: 3, 2: 1, 3: 2}, just_done_by=1), 2, "équité : le moins servi")

# Équité, égalité de compteur : celui qui l'a faite il y a le plus longtemps.
last_done = {1: dt.datetime(2026, 7, 1), 2: dt.datetime(2026, 6, 1), 3: dt.datetime(2026, 7, 20)}
check(rotate("equity", {1: 2, 2: 2, 3: 2}, last_done), 2, "équité : le plus ancien départage")

# Quelqu'un qui n'a jamais fait la tâche passe devant.
check(rotate("equity", {1: 1, 2: 1, 3: 0}, last_done), 3, "équité : jamais fait = prioritaire")

# Rattrapage : celui qui est en retard peut enchaîner, c'est voulu.
check(rotate("equity", {1: 5, 2: 3, 3: 5}, just_done_by=2), 2, "équité : rattrapage en série")

print(f"OK — {checks} vérifications passées")
