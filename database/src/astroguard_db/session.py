"""Engine creation. Every SQLite connection enforces foreign keys."""
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url


def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite and parsed.database not in (None, "", ":memory:") and not parsed.database.startswith("file:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if is_sqlite:
        event.listen(engine, "connect", _enable_foreign_keys)
    return engine
