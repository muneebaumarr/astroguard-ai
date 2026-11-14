"""Database location. Override with the DATABASE_URL environment variable."""
import os
from pathlib import Path

# database/var/astroguard.db  (the var/ folder and *.db files are git-ignored)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "var" / "astroguard.db"


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///" + DEFAULT_DB_PATH.as_posix()
