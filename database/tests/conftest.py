"""Every test gets its own temporary SQLite file. The development database is never touched."""
import pytest

from astroguard_db import SqliteAdapterFactory
from astroguard_db.migrate import upgrade
from astroguard_db.seed import seed


@pytest.fixture
def db_url(tmp_path):
    return "sqlite:///" + (tmp_path / "test.db").as_posix()


@pytest.fixture
def factory(db_url):
    upgrade(db_url)
    adapter = SqliteAdapterFactory(db_url)
    yield adapter
    adapter.dispose()


@pytest.fixture
def seeded(factory):
    assert seed(factory) is True
    return factory
