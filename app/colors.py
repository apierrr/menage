"""Palette des tuiles.

Le rouge est réservé à l'état « en retard » : si une tuile pouvait être rouge,
on ne saurait plus lire la page d'un coup d'œil. Il est donc exclu du
sélecteur, et refusé côté serveur pour que ça reste vrai quoi qu'il arrive.
"""

from __future__ import annotations

import colorsys
import re

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Teintes proposées dans le sélecteur (aucune dans la zone rouge).
PALETTE = [
    "#f97316", "#ea580c", "#f59e0b", "#ca8a04",
    "#84cc16", "#65a30d", "#22c55e", "#16a34a",
    "#10b981", "#0d9488", "#14b8a6", "#06b6d4",
    "#0ea5e9", "#0284c7", "#3b82f6", "#2563eb",
    "#6366f1", "#4f46e5", "#8b5cf6", "#7c3aed",
    "#a855f7", "#9333ea", "#c026d3", "#d946ef",
    "#64748b", "#475569", "#78716c", "#57534e",
]

# Couleurs d'état, non sélectionnables.
OVERDUE_COLOR = "#dc2626"

# Zone de teintes interdites (en degrés) et seuil de saturation associé.
# On coupe assez large côté rose : un framboise soutenu se confond avec le
# rouge « en retard » sur une tuile.
RED_HUE_MIN = 330.0
RED_HUE_MAX = 14.0
RED_SATURATION_MIN = 0.35


def to_hsl(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, saturation, lightness


def is_reserved_red(hex_color: str) -> bool:
    hue, saturation, lightness = to_hsl(hex_color)
    if saturation < RED_SATURATION_MIN or lightness > 0.82:
        return False
    return hue >= RED_HUE_MIN or hue <= RED_HUE_MAX


def normalize(hex_color: str, fallback: str = "#3b82f6") -> str:
    if not hex_color or not HEX_RE.match(hex_color):
        return fallback
    return hex_color.lower()


def validate(hex_color: str) -> str:
    """Renvoie la couleur normalisée, ou lève une ValueError si elle est rouge."""
    if not hex_color or not HEX_RE.match(hex_color):
        raise ValueError("Couleur invalide (format attendu : #rrggbb)")
    if is_reserved_red(hex_color):
        raise ValueError("Le rouge est réservé aux tâches en retard")
    return hex_color.lower()
