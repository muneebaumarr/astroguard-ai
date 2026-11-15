"""Runtime adapter selection. SQLite remains an independently installed package."""
from .memory import MemoryAdapterFactory


def create_adapter(settings):
    if settings.repository_backend == 'memory':
        return MemoryAdapterFactory()
    if settings.repository_backend != 'sqlite':
        raise RuntimeError(f"Unsupported REPOSITORY_BACKEND={settings.repository_backend!r}; no memory fallback is allowed.")
    try:
        from astroguard_db import SqliteAdapterFactory
        from astroguard_db.config import database_url
        from sqlalchemy.engine import make_url
    except ImportError as exc:
        raise RuntimeError('SQLite requires the independent database package. Install -e ./database and the backend sqlite extra; no memory fallback is allowed.') from exc
    url = settings.database_url or database_url()
    parsed = make_url(url)
    if parsed.get_backend_name() != 'sqlite' or parsed.database in (None, '', ':memory:'):
        raise RuntimeError('SQLite backend requires a file-backed SQLite DATABASE_URL; no memory fallback is allowed.')
    return SqliteAdapterFactory(url)


def close_adapter(adapter):
    dispose = getattr(adapter, 'dispose', None)
    if dispose is not None:
        dispose()
    else:
        adapter.close()
