"""Vérifie qu'aucune classe CSS de l'app n'est masquée par un bloqueur.

Un filtre cosmétique « nu » comme `##.share-bar` masque *tout* élément portant
cette classe, sur n'importe quel site. C'est ce qui a rendu l'indicateur des
tâches ponctuelles invisible pour qui active EasyList Social Widgets : la jauge
s'appelait `.share-bar` et les chiffres `.share-legend`.

    python3 tests/check_classes.py

Sortie non nulle si une classe de l'app est visée.
"""

from __future__ import annotations

import pathlib
import re
import sys
import urllib.request

LISTS = {
    "EasyList": "https://easylist.to/easylist/easylist.txt",
    "EasyList Social": "https://easylist.to/easylist/fanboy-social.txt",
    "EasyPrivacy": "https://easylist.to/easylist/easyprivacy.txt",
    "uBlock": "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt",
}

SRC = pathlib.Path(__file__).resolve().parents[1] / "web" / "src"


def bare_filters() -> set[str]:
    """Classes masquées quel que soit le site."""
    classes: set[str] = set()
    for name, url in LISTS.items():
        # easylist.to renvoie 403 à l'agent par défaut d'urllib.
        request = urllib.request.Request(url, headers={"User-Agent": "menage-selfcheck/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read().decode(errors="ignore")
        except OSError as error:  # pragma: no cover - dépend du réseau
            print(f"  ! {name} injoignable ({error})")
            continue
        found = 0
        for line in body.splitlines():
            if not line.startswith("##"):
                continue
            selector = line[2:].strip()
            if re.fullmatch(r"\.[A-Za-z0-9_-]+", selector):
                classes.add(selector[1:])
                found += 1
        print(f"  · {name}: {found} filtres nus")
    return classes


def app_classes() -> set[str]:
    """Classes réellement utilisées, commentaires exclus."""
    used: set[str] = set()
    for path in SRC.rglob("*"):
        if path.suffix not in (".css", ".jsx"):
            continue
        text = path.read_text()
        if path.suffix == ".css":
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            used.update(re.findall(r"\.([a-z][a-z0-9-]*)", text))
        else:
            text = re.sub(r"//.*", "", text)
            for attribute in re.findall(r"className=[{\"'`]([^\"'`}]+)", text):
                used.update(w for w in attribute.split() if re.fullmatch(r"[a-z][a-z0-9-]*", w))
    return used


print("Listes de filtres :")
blocked = bare_filters()
mine = app_classes()

# Contrôle négatif : ces deux-là doivent être détectés, sinon le test ne teste rien.
control = [name for name in ("share-bar", "share-legend") if name in blocked]
if len(control) != 2:
    print("\nATTENTION : le contrôle négatif échoue, les listes ont-elles changé ?")

hits = sorted(name for name in mine if name in blocked)
print(f"\n{len(mine)} classes dans l'app, {len(blocked)} classes masquées par les listes")
print("contrôle négatif (doit trouver les 2 anciens noms) :", control)

if hits:
    print("\nCLASSES BLOQUÉES — à renommer :")
    for name in hits:
        print("  .", name, sep="")
    sys.exit(1)

print("\nAucune classe de l'app n'est masquée.")
