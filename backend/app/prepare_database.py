"""Explicit migration/seed command; application GET/startup never seeds data."""
import argparse

from app.core.config import Settings
from app.repositories.factory import create_adapter, close_adapter


def main():
    parser = argparse.ArgumentParser(description='Migrate the configured AstroGuard SQLite database.')
    parser.add_argument('--seed', action='store_true', help='Add shared fictional fixtures if the demo mission is absent.')
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.repository_backend != 'sqlite':
        raise RuntimeError('Set REPOSITORY_BACKEND=sqlite in backend/.env or the environment before preparing the database.')
    from astroguard_db.migrate import upgrade
    from astroguard_db.seed import seed
    adapter = create_adapter(settings)
    try:
        upgrade(adapter.database_url)
        print('SQLite migrations applied.')
        if args.seed:
            added = seed(adapter)
            print('Shared fictional fixtures added.' if added else 'Demo mission already exists; no seed records modified. Partial fixture sets are not repaired automatically.')
        if not adapter.check_ready().ready:
            raise RuntimeError('SQLite is not ready after migration.')
    finally:
        close_adapter(adapter)


if __name__ == '__main__':
    main()
