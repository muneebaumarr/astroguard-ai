"""Load the shared fictional fixtures into the database.

Run from the repository root:  python -m astroguard_db.seed
Safe to run more than once: if the demo mission already exists, nothing is added.
"""
from astroguard_contracts.fixtures import MISSION_ID, representative_fixtures

from .config import database_url
from .factory import SqliteAdapterFactory
from .migrate import upgrade


def seed(factory: SqliteAdapterFactory) -> bool:
    """Insert all fixtures in one transaction. Returns False if already seeded."""
    fixtures = representative_fixtures()
    with factory.create_uow() as uow:
        if uow.missions.get(MISSION_ID) is not None:
            return False
        for mission in fixtures["missions"]:
            uow.missions.add(mission)
        for astronaut in fixtures["astronauts"]:
            uow.astronauts.add(astronaut)
        for run in fixtures["simulation_runs"]:
            uow.simulation_runs.add(run)
        for checkin in fixtures["checkins"]:
            uow.checkins.add(checkin)
        uow.health_readings.add_many(fixtures["health_readings"])
        uow.environmental_readings.add_many(fixtures["environmental_readings"])
        for assessment in fixtures["assessments"]:
            uow.assessments.add(assessment)
        for alert in fixtures["alerts"]:
            uow.alerts.add(alert)
        for receipt in fixtures["command_receipts"]:
            uow.command_receipts.add(receipt)
        uow.commit()
    return True


def main() -> None:
    url = database_url()
    upgrade(url)
    factory = SqliteAdapterFactory(url)
    try:
        created = seed(factory)
    finally:
        factory.dispose()
    print("Fictional demo data added." if created else "Demo data already present; nothing added.")


if __name__ == "__main__":
    main()
