from pathlib import Path

from sqlalchemy import create_engine, inspect

import astroguard_db
from astroguard_db import SqliteAdapterFactory
from astroguard_db.migrate import upgrade
from astroguard_db.models import REQUIRED_TABLES, Base

EXPECTED_TABLES = {
    "missions", "astronauts", "daily_checkins", "health_readings", "environmental_readings",
    "assessments", "alerts", "simulation_runs", "command_receipts",
}


def _inspect(db_url):
    engine = create_engine(db_url)
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        columns = {t: {c["name"] for c in insp.get_columns(t)} for t in tables}
        indexes = {t: {i["name"] for i in insp.get_indexes(t)} for t in tables}
    finally:
        engine.dispose()
    return tables, columns, indexes


def test_models_define_the_nine_contract_tables():
    assert set(REQUIRED_TABLES) == EXPECTED_TABLES


def test_fresh_migration_creates_all_tables(db_url):
    upgrade(db_url)
    tables, _, _ = _inspect(db_url)
    assert EXPECTED_TABLES <= tables
    assert "alembic_version" in tables


def test_migration_matches_models(db_url):
    upgrade(db_url)
    _, columns, indexes = _inspect(db_url)
    for table in Base.metadata.sorted_tables:
        assert columns[table.name] == {c.name for c in table.columns}, table.name
        for index in table.indexes:
            assert index.name in indexes[table.name], f"{table.name}.{index.name}"


def test_upgrade_twice_is_safe(db_url):
    upgrade(db_url)
    upgrade(db_url)


def test_not_ready_before_migration(db_url):
    adapter = SqliteAdapterFactory(db_url)
    try:
        result = adapter.check_ready()
    finally:
        adapter.dispose()
    assert result.ready is False
    assert result.adapter == "sqlite"
    assert result.detail


def test_ready_after_migration(factory):
    result = factory.check_ready()
    assert result.ready is True
    assert result.adapter == "sqlite"


def test_package_never_imports_backend_or_fastapi():
    package_dir = Path(astroguard_db.__file__).parent
    forbidden = ("import fastapi", "from fastapi", "import backend", "from backend", "from app")
    for source in package_dir.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in text, f"{source.name} contains '{word}'"
