"""Run Alembic migrations from Python (same as: alembic -c database/alembic.ini upgrade head)."""
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import database_url as default_database_url

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config(database_url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    url = database_url or default_database_url()
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def upgrade(database_url: str | None = None, revision: str = "head") -> None:
    command.upgrade(alembic_config(database_url), revision)


if __name__ == "__main__":
    upgrade()
    print("Database migrated to the latest version.")
