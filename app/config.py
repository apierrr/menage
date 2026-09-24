"""Configuration de l'application, lue depuis l'environnement."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'menage.db'}")

TIMEZONE = os.getenv("TZ", "Europe/Paris")

# Fenêtre glissante utilisée pour le % de répartition des tâches ponctuelles.
SHARE_WINDOW_DAYS = int(os.getenv("SHARE_WINDOW_DAYS", "90"))

# Durée de vie du cookie d'identité (1 an).
SESSION_COOKIE = "menage_user"
SESSION_MAX_AGE = 365 * 24 * 3600


def get_secret_key() -> str:
    """Clé de signature du cookie.

    Prise dans l'environnement si fournie, sinon générée une fois et conservée
    dans le volume de données — ça évite d'imposer un .env pour démarrer.
    """
    from_env = os.getenv("SECRET_KEY")
    if from_env:
        return from_env

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key_file = DATA_DIR / "secret.key"
    if key_file.exists():
        content = key_file.read_text().strip()
        if content:
            return content

    key = secrets.token_urlsafe(48)
    key_file.write_text(key)
    key_file.chmod(0o600)
    return key
