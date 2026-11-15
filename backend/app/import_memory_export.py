"""Explicit, atomic import of a reviewed pre-SQLite API export. Never runs at startup."""
import argparse
import json
from pathlib import Path

from astroguard_contracts import dto as d
from astroguard_contracts.errors import Conflict
from app.core.config import Settings
from app.repositories.factory import create_adapter, close_adapter


def collect(repository, owner, query_cls):
    records = []
    while True:
        page = repository.list(owner, query_cls(limit=1000, offset=len(records)))
        records.extend(page.items)
        if len(records) >= page.total:
            return records
        if not page.items:
            raise RuntimeError('Incomplete database page during import')


def import_export(adapter, payload):
    if payload.get('format') != 'astroguard-pre-sqlite-api-export-v1':
        raise ValueError('Unsupported memory export format')
    models = {'missions': d.Mission, 'astronauts': d.Astronaut, 'simulation_runs': d.SimulationRun,
        'checkins': d.DailyCheckin, 'readings': d.HealthReading, 'environmental_readings': d.EnvironmentalReading,
        'assessments': d.Assessment, 'alerts': d.Alert}
    values = {name: [model.model_validate(item) for item in payload[name]] for name, model in models.items()}
    # Canonical vital order matches check-in responses and SQLite reconstruction.
    values['checkins'] = [d.DailyCheckin.model_validate(record.model_dump() | {'readings': sorted(record.readings, key=lambda r: r.indicator)}) for record in values['checkins']]
    added = {name: 0 for name in models}
    with adapter.create_uow() as uow:
        for name in ('missions', 'astronauts'):
            repository = getattr(uow, name)
            for record in values[name]:
                existing = repository.get(record.id)
                if existing and existing != record:
                    raise Conflict(f'Existing {name} record differs from export; refusing overwrite')
                if existing is None:
                    repository.add(record); added[name] += 1
        existing_runs = {record.id: uow.simulation_runs.get(record.id) for record in values['simulation_runs']}
        # Release seeded active slots before adding another active exported run.
        for record in values['simulation_runs']:
            existing = existing_runs[record.id]
            if existing and existing != record:
                if record.last_tick_index < existing.last_tick_index:
                    raise Conflict('Export run is older than stored progress; refusing to rewind it')
                uow.simulation_runs.update(record, expected_last_tick=existing.last_tick_index)
        for record in values['simulation_runs']:
            if existing_runs[record.id] is None:
                uow.simulation_runs.add(record); added['simulation_runs'] += 1
        for record in values['checkins']:
            existing = uow.checkins.get(record.id)
            if existing and existing != record:
                raise Conflict('Existing check-in differs from export; refusing overwrite')
            if existing is None:
                uow.checkins.add(record); added['checkins'] += 1
        for name, repository, owners, query in (
            ('readings', uow.health_readings, values['astronauts'], d.HealthReadingQuery),
            ('environmental_readings', uow.environmental_readings, values['missions'], d.EnvironmentalReadingQuery),
        ):
            existing = {item.id: item for owner in owners for item in collect(repository, owner.id, query)}
            new = []
            for record in values[name]:
                if record.id in existing and existing[record.id] != record:
                    raise Conflict(f'Existing {name} record differs from export; refusing overwrite')
                if record.id not in existing:
                    new.append(record)
            repository.add_many(new); added[name] = len(new)
        for record in values['assessments']:
            existing = uow.assessments.get(record.id)
            if existing and existing != record:
                raise Conflict('Existing assessment differs from export; refusing overwrite')
            if existing is None:
                uow.assessments.add(record); added['assessments'] += 1
        for record in values['alerts']:
            existing = uow.alerts.get(record.id)
            if existing is None:
                uow.alerts.add(record); added['alerts'] += 1
            elif existing != record:
                uow.alerts.update(record)
        # Verify every imported check-in reconstructs exactly from its actual linked readings.
        for record in values['checkins']:
            if uow.checkins.get(record.id) != record:
                raise Conflict('Export check-in does not match its linked readings')
        uow.commit()
    return added


def main():
    parser = argparse.ArgumentParser(description='Import a reviewed memory API export into SQLite without fabricating command receipts.')
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.repository_backend != 'sqlite':
        raise RuntimeError('Set REPOSITORY_BACKEND=sqlite before importing.')
    adapter = create_adapter(settings)
    try:
        if not adapter.check_ready().ready:
            raise RuntimeError('Migrate the SQLite database before importing.')
        print(json.dumps(import_export(adapter, json.loads(args.path.read_text(encoding='utf-8')))))
        print('Imported API-visible records. Historical memory command receipts were not available; new commands persist normally.')
    finally:
        close_adapter(adapter)


if __name__ == '__main__':
    main()
