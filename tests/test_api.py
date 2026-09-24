"""Test fonctionnel de bout en bout, à exécuter dans un container jetable.

    docker run -d --name menage-test -e DATA_DIR=/tmp/mt \
      -e DATABASE_URL=sqlite:////tmp/mt/test.db menage-test
    docker exec -i menage-test python - < tests/test_api.py
"""

from __future__ import annotations

import calendar
import datetime as dt
import json
import time
import urllib.error
import urllib.request
from http import cookiejar

BASE = "http://127.0.0.1:8000"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar.CookieJar()))
checks = 0


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    with opener.open(request, timeout=10) as response:
        body = response.read()
    return json.loads(body) if body else None


def check(actual, expected, label):
    global checks
    assert actual == expected, f"{label} : attendu {expected!r}, obtenu {actual!r}"
    checks += 1


def truthy(value, label):
    global checks
    assert value, f"{label} : attendu vrai, obtenu {value!r}"
    checks += 1


# Attente du démarrage d'uvicorn.
for attempt in range(40):
    try:
        call("GET", "/healthz")
        break
    except (urllib.error.URLError, ConnectionError):
        time.sleep(0.25)
else:
    raise SystemExit("le serveur ne répond pas")

today = dt.date.today()
iso = lambda d: d.isoformat()  # noqa: E731


def add_month(date: dt.date) -> dt.date:
    """Le mois suivant, ramené au dernier jour quand le jour n'existe pas."""
    year, month = (date.year + 1, 1) if date.month == 12 else (date.year, date.month + 1)
    return dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1]))

# --- Installation -----------------------------------------------------------

state = call("GET", "/api/bootstrap")
check(state["setup_done"], False, "avant installation")
truthy(len(state["palette"]) > 10, "palette fournie")
truthy(all(color != "#dc2626" for color in state["palette"]), "pas de rouge dans la palette")

state = call(
    "POST",
    "/api/setup",
    {
        "users": [
            {"name": "Alice", "color": "#3b82f6"},
            {"name": "Bob", "color": "#22c55e"},
            {"name": "Chloé", "color": "#a855f7"},
        ]
    },
)
check(state["setup_done"], True, "après installation")
check([u["name"] for u in state["users"]], ["Alice", "Bob", "Chloé"], "ordre des profils")
alice, bob, chloe = (u["id"] for u in state["users"])

# Le rouge est refusé côté serveur, même en forçant l'API.
try:
    call("POST", "/api/users", {"name": "Rouge", "color": "#dc2626"})
    raise AssertionError("le rouge aurait dû être refusé")
except urllib.error.HTTPError as error:
    check(error.code, 422, "couleur rouge refusée")

# --- Identité ---------------------------------------------------------------

call("POST", "/api/session", {"user_id": alice})
check(call("GET", "/api/bootstrap")["me"]["name"], "Alice", "identité mémorisée par cookie")

# --- Tâches régulières ------------------------------------------------------

late = call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "title": "Salle de bain",
        "color": "#0ea5e9",
        "bullets": ["sol", "miroir"],
        "period_kind": "week",
        "period_n": 1,
        "assignee_id": alice,
        "due_date": iso(today - dt.timedelta(days=2)),
    },
)
check(late["regular"]["days_left"], -2, "compteur négatif quand la date est passée")
check(late["regular"]["is_overdue"], True, "tuile en retard")
check(late["bullets"], ["sol", "miroir"], "puces enregistrées")

soon = call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "title": "Poussière",
        "color": "#8b5cf6",
        "period_kind": "week",
        "period_n": 2,
        "assignee_id": bob,
        "due_date": iso(today + dt.timedelta(days=3)),
    },
)
check(soon["regular"]["days_left"], 3, "compteur en jours pleins")
check(soon["regular"]["assignee"]["name"], "Bob", "premier responsable choisi à la création")
# La couleur envoyée est ignorée : une tâche régulière porte celle de son responsable.
check(soon["color"], "#22c55e", "la tuile prend la couleur de Bob")

# Tri : ce qui est à moi passe devant, le plus urgent d'abord.
page = call("GET", "/api/tiles?section=regular")
check([t["title"] for t in page["tiles"]], ["Salle de bain", "Poussière"], "mes tâches d'abord")
check(page["tiles"][0]["regular"]["is_mine"], True, "la première est bien à moi")
check(page["tiles"][1]["regular"]["is_mine"], False, "la seconde est à quelqu'un d'autre")

# L'ordre manuel reste accessible.
call("POST", "/api/tiles/reorder", {"section": "regular", "ids": [soon["id"], late["id"]]})
manual = call("GET", "/api/tiles?section=regular&sort=manual")
check([t["title"] for t in manual["tiles"]], ["Poussière", "Salle de bain"], "ordre manuel respecté")
auto = call("GET", "/api/tiles?section=regular")
check([t["title"] for t in auto["tiles"]], ["Salle de bain", "Poussière"], "tri auto reprend la main")

# --- Validation, rotation, échéance -----------------------------------------

result = call("POST", f"/api/tiles/{late['id']}/complete")
done = result["tile"]
check(done["regular"]["assignee"]["name"], "Bob", "équité : Bob n'avait jamais fait la tâche")
check(done["color"], "#22c55e", "la couleur de la tuile suit la rotation")
check(done["regular"]["due_date"], iso(today + dt.timedelta(days=7)), "retard : on repart de la validation")
check(done["regular"]["is_overdue"], False, "plus en retard après validation")

# Annulation : on retrouve exactement l'état d'avant.
call("DELETE", f"/api/completions/{result['completion_id']}")
back = call("GET", "/api/tiles?section=regular")["tiles"][0]
check(back["regular"]["due_date"], iso(today - dt.timedelta(days=2)), "annulation : échéance restaurée")
check(back["regular"]["assignee"]["name"], "Alice", "annulation : responsable restauré")

# On revalide, puis on rappuie : valider veut dire « c'est fait, le compteur
# repart à sept jours », pas « ajoute sept jours ».
first = call("POST", f"/api/tiles/{late['id']}/complete")
due_after_first = first["tile"]["regular"]["due_date"]
check(due_after_first, iso(today + dt.timedelta(days=7)), "le compteur repart à sept jours")
check(first["repeat"], False, "première validation du jour")
check(first["tile"]["regular"]["done_today"], True, "la tuile est marquée faite aujourd'hui")

for tap in (2, 3):
    again = call("POST", f"/api/tiles/{late['id']}/complete")
    check(again["repeat"], True, f"{tap}e appui signalé comme répétition")
    check(again["completion_id"], first["completion_id"], f"{tap}e appui : pas de doublon")
    check(again["tile"]["regular"]["due_date"], due_after_first, f"{tap}e appui : échéance stable")

after_taps = next(
    t for t in call("GET", "/api/tiles?section=regular")["tiles"] if t["id"] == late["id"]
)
check(after_taps["regular"]["due_date"], due_after_first, "trois appuis, une seule échéance")
check(after_taps["regular"]["assignee"]["name"], "Bob", "le responsable n'a tourné qu'une fois")

# Validation en avance : le compteur repart quand même du jour de la validation.
call("POST", "/api/session", {"user_id": alice})
early = call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "title": "Détartrage",
        "color": "#14b8a6",
        "period_kind": "month",
        "period_n": 1,
        "assignee_id": alice,
        "due_date": "2026-12-31",
    },
)
early_done = call("POST", f"/api/tiles/{early['id']}/complete")["tile"]
expected = add_month(today)
check(early_done["regular"]["due_date"], iso(expected), "avance : un mois plein depuis aujourd'hui")

# Quelqu'un d'autre valide la même tâche le même jour : ça compte pour lui, mais
# l'échéance ne se recalcule pas — le jour de référence mensuel ne dérive pas.
call("POST", "/api/session", {"user_id": bob})
also = call("POST", f"/api/tiles/{early['id']}/complete")
check(also["repeat"], False, "une autre personne valide pour de bon")
check(also["tile"]["regular"]["due_date"], iso(expected), "échéance calculée une seule fois")
call("POST", "/api/session", {"user_id": alice})

# --- Tâches ponctuelles -----------------------------------------------------

trash = call(
    "POST",
    "/api/tiles",
    {"section": "oneoff", "kind": "task", "title": "Poubelles", "color": "#f97316"},
)
check(trash["oneoff"]["total"], 0, "aucune validation au départ")
# Une tâche ponctuelle n'a pas de responsable : sa couleur reste au choix.
check(trash["color"], "#f97316", "la couleur choisie est conservée en ponctuel")

for _ in range(3):
    call("POST", f"/api/tiles/{trash['id']}/complete")
call("POST", "/api/session", {"user_id": bob})
call("POST", f"/api/tiles/{trash['id']}/complete")
call("POST", "/api/session", {"user_id": alice})

share = call("GET", "/api/tiles?section=oneoff")["tiles"][0]["oneoff"]
check(share["total"], 4, "quatre validations comptées")
check({s["user_id"]: s["pct"] for s in share["shares"]}, {alice: 75.0, bob: 25.0, chloe: 0.0}, "répartition en %")
check(share["window_days"], 90, "fenêtre glissante de 90 jours")

# --- Sous-menus -------------------------------------------------------------

folder = call(
    "POST",
    "/api/tiles",
    {"section": "regular", "kind": "folder", "title": "Cuisine", "color": "#65a30d"},
)
child = call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "parent_id": folder["id"],
        "title": "Four",
        "period_kind": "month",
        "period_n": 1,
        "assignee_id": alice,
        "due_date": iso(today + dt.timedelta(days=1)),
    },
)
# Deux tâches de plus pour Bob, dont une dans un sous-sous-menu : la couleur du
# dossier doit se partager au prorata, à n'importe quelle profondeur.
call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "parent_id": folder["id"],
        "title": "Plan de travail",
        "period_kind": "week",
        "period_n": 1,
        "assignee_id": bob,
        "due_date": iso(today + dt.timedelta(days=5)),
    },
)
shelf = call(
    "POST",
    "/api/tiles",
    {"section": "regular", "kind": "folder", "parent_id": folder["id"], "title": "Placards"},
)
call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "kind": "task",
        "parent_id": shelf["id"],
        "title": "Vaisselier",
        "period_kind": "month",
        "period_n": 1,
        "assignee_id": bob,
        "due_date": iso(today + dt.timedelta(days=10)),
    },
)

root = call("GET", "/api/tiles?section=regular")
folder_tile = next(t for t in root["tiles"] if t["id"] == folder["id"])
check(folder_tile["folder"]["task_count"], 3, "le dossier compte les tâches à toute profondeur")
check(folder_tile["folder"]["days_left"], 1, "le dossier remonte l'échéance la plus proche")
check(folder_tile["folder"]["is_mine"], True, "le dossier signale que ça me concerne")

mix = folder_tile["folder"]["mix"]
check([(p["name"], p["count"]) for p in mix], [("Alice", 1), ("Bob", 2)], "ma part en premier")
check([p["pct"] for p in mix], [33.33, 66.67], "un tiers pour moi, deux tiers pour Bob")
# Le dossier a été créé avec une couleur : elle est ignorée, seul le dessous compte.
check(folder_tile["color"], "#22c55e", "la teinte dominante est celle de Bob")

inside = call(f"GET", f"/api/tiles?section=regular&parent_id={folder['id']}")
check([t["title"] for t in inside["tiles"]], ["Four", "Plan de travail", "Placards"], "contenu du sous-menu")
check([c["title"] for c in inside["breadcrumb"]], ["Cuisine"], "fil d'ariane")
nested = next(t for t in inside["tiles"] if t["id"] == shelf["id"])
check([(p["name"], p["pct"]) for p in nested["folder"]["mix"]], [("Bob", 100.0)], "sous-sous-menu tout à Bob")

# Un sous-menu vide n'a rien à refléter.
empty = call("POST", "/api/tiles", {"section": "regular", "kind": "folder", "title": "Cave"})
check(empty["folder"]["mix"], [], "un sous-menu vide ne reflète aucune couleur")
check(empty["color"], "#475569", "et reste neutre")

# --- Profil ajouté après coup ----------------------------------------------

david = call("POST", "/api/users", {"name": "David", "color": "#0284c7"})
after = call("GET", "/api/tiles?section=regular")
still = next(t for t in after["tiles"] if t["id"] == late["id"])
check(
    still["regular"]["assignee"]["name"],
    "Bob",
    "un nouvel arrivant ne rafle pas les tâches en cours",
)

# --- Récapitulatif ----------------------------------------------------------

stats = call("GET", "/api/stats")
check(stats["global"]["users"], 4, "quatre profils")
check(stats["global"]["oneoff_tasks"], 1, "une tâche ponctuelle")
# 1 sur « Salle de bain » (les rappuis ne comptent pas, l'annulée non plus),
# 2 détartrages (Alice puis Bob le même jour), 4 poubelles.
check(stats["global"]["done"], 7, "sept validations sur la fenêtre")
check(next(u for u in stats["users"] if u["id"] == alice)["is_me"], True, "je suis identifiée")
truthy(any(u["overdue"] == 0 for u in stats["users"]), "indicateur de retard présent")

# --- Historique -------------------------------------------------------------

entries = call("GET", "/api/history")["entries"]
check(len(entries), 7, "sept entrées au journal")
check(entries[0]["tile_title"], "Poubelles", "la plus récente en tête")
check(entries[0]["user"]["name"], "Bob", "avec son auteur")
truthy(entries[0]["at"].startswith(iso(today)), "horodatée en heure locale")
check(sum(1 for e in entries if e["is_last"]), 3, "une dernière validation par tuile")

# Supprimer une validation ancienne : elle sort des compteurs, sans toucher à
# l'échéance en cours.
old = next(e for e in entries if e["tile_title"] == "Poubelles" and not e["is_last"])
call("DELETE", f"/api/completions/{old['id']}")
check(len(call("GET", "/api/history")["entries"]), 6, "entrée ancienne supprimée")
check(
    call("GET", "/api/tiles?section=oneoff")["tiles"][0]["oneoff"]["total"],
    3,
    "le compteur de la tuile a été réduit",
)

# --- Tâche quotidienne ------------------------------------------------------

call("POST", "/api/session", {"user_id": alice})
daily = call(
    "POST",
    "/api/tiles",
    {"section": "regular", "title": "Vaisselle", "period_kind": "day", "period_n": 1},
)
check(daily["regular"]["due_date"], iso(today), "quotidienne : à faire dès aujourd'hui")
done = call("POST", f"/api/tiles/{daily['id']}/complete")["tile"]
check(done["regular"]["due_date"], iso(today + dt.timedelta(days=1)), "quotidienne : revient demain")

# --- Personnes concernées ---------------------------------------------------

duo = call(
    "POST",
    "/api/tiles",
    {
        "section": "regular",
        "title": "Aspirateur",
        "period_kind": "week",
        "period_n": 1,
        "member_ids": [bob, chloe],
    },
)
check(sorted(duo["members"]), sorted([bob, chloe]), "personnes concernées enregistrées")
check(duo["regular"]["assignee"]["id"], bob, "Alice non concernée : Bob commence")

# La rotation ne tourne qu'entre Bob et Chloé, même si c'est Alice qui valide.
turns = []
for _ in range(4):
    duo = call("POST", f"/api/tiles/{duo['id']}/complete")["tile"]
    turns.append(duo["regular"]["assignee"]["id"])
    call("DELETE", "/api/session")
    call("POST", "/api/session", {"user_id": duo["regular"]["assignee"]["id"]})
truthy(all(t in (bob, chloe) for t in turns), "rotation limitée aux personnes concernées")
call("POST", "/api/session", {"user_id": alice})

try:
    call("PATCH", f"/api/tiles/{duo['id']}", {"assignee_id": alice})
    raise AssertionError("Alice n'est pas concernée, elle ne peut pas être responsable")
except urllib.error.HTTPError as error:
    check(error.code, 400, "responsable hors des personnes concernées refusé")

# Réservée à une seule personne : c'est toujours elle.
solo = call("PATCH", f"/api/tiles/{duo['id']}", {"member_ids": [chloe]})
check(solo["regular"]["assignee"]["id"], chloe, "décocher le responsable passe la main")
solo = call("POST", f"/api/tiles/{solo['id']}/complete")["tile"]
check(solo["regular"]["assignee"]["id"], chloe, "une seule personne : toujours elle")

# Tout le monde coché = aucune restriction (les futurs profils suivront).
everyone = call("PATCH", f"/api/tiles/{solo['id']}", {"member_ids": [alice, bob, chloe, david["id"]]})
check(everyone["members"], None, "tout le monde coché = pas de restriction")

# Ponctuelle réservée : la jauge ne compte que les personnes concernées.
pair = call(
    "POST",
    "/api/tiles",
    {"section": "oneoff", "title": "Vitres", "member_ids": [alice, bob]},
)
check(
    sorted(s["user_id"] for s in pair["oneoff"]["shares"]),
    sorted([alice, bob]),
    "ponctuelle : jauge limitée aux personnes concernées",
)

# Un nouveau profil ne rejoint pas une tâche réservée.
restricted = call(
    "POST",
    "/api/tiles",
    {"section": "regular", "title": "Litière", "period_kind": "week", "member_ids": [alice]},
)
emma = call("POST", "/api/users", {"name": "Emma", "color": "#16a34a"})
restricted = next(
    t for t in call("GET", "/api/tiles?section=regular")["tiles"] if t["id"] == restricted["id"]
)
check(restricted["members"], [alice], "nouveau profil absent d'une tâche réservée")

# --- Suppression en cascade -------------------------------------------------

call("DELETE", f"/api/tiles/{folder['id']}")
check(
    [t["id"] for t in call("GET", "/api/tiles?section=regular")["tiles"] if t["id"] == folder["id"]],
    [],
    "dossier supprimé",
)
try:
    call("GET", f"/api/tiles?section=regular&parent_id={child['id']}")
    raise AssertionError("la tâche fille aurait dû disparaître avec son dossier")
except urllib.error.HTTPError as error:
    check(error.code, 404, "suppression en cascade du contenu")

print(f"OK — {checks} vérifications passées")
