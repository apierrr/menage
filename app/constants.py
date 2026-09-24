"""Valeurs partagées, sans dépendance — pour que le moteur reste testable seul."""

# Sections racines : les deux tuiles pleine largeur de l'accueil.
SECTION_REGULAR = "regular"
SECTION_ONEOFF = "oneoff"

KIND_FOLDER = "folder"
KIND_TASK = "task"

PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"

ROTATION_EQUITY = "equity"            # celui qui l'a faite le moins souvent
ROTATION_ROUND_ROBIN = "round_robin"  # chacun son tour, dans l'ordre des profils
