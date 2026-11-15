from copy import deepcopy
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from astroguard_contracts import dto as d
from app.main import create_app
from app.core.config import Settings
from app.repositories.memory import MemoryAdapterFactory
from app.services.education import hazards, guidance


@pytest.fixture
def client():
    with TestClient(create_app(Settings(), MemoryAdapterFactory())) as client:
        yield client


def test_five_hazards_are_typed_stable_and_have_verified_official_sources(client):
    first = client.get('/api/v1/hazards')
    assert first.status_code == 200
    page = d.Page[d.Hazard].model_validate(first.json())
    assert page.total == 5
    assert {item.slug for item in page.items} == {'space_radiation', 'isolation_confinement', 'distance_from_earth', 'gravity_fields', 'hostile_closed_environments'}
    assert first.json() == client.get('/api/v1/hazards').json()
    for item in page.items:
        assert 'Why it matters:' in item.description and 'Crew and operations:' in item.description and 'Preparedness concepts:' in item.description
        assert item.monitoring_limitations and item.references
        assert all(urlparse(reference.url).hostname == 'www.nasa.gov' for reference in item.references)
        detail = client.get('/api/v1/hazards/' + item.slug)
        assert d.Hazard.model_validate(detail.json()) == item


def test_all_six_guidance_topics_validate_and_retain_limitations(client):
    response = client.get('/api/v1/guidance')
    page = d.Page[d.GuidanceArticle].model_validate(response.json())
    assert page.total == 6 and response.json() == client.get('/api/v1/guidance').json()
    assert {item.slug for item in page.items} == {'sleep_circadian', 'exercise_conditioning', 'hydration_nutrition', 'crew_wellbeing', 'environmental_monitoring', 'radiation_awareness'}
    for item in page.items:
        assert 'Spaceflight context:' in item.educational_text and 'Educational considerations:' in item.educational_text
        assert 'not individual medical advice' in item.limitations and 'do not endorse' in item.limitations
        assert all(urlparse(reference.url).hostname == 'www.nasa.gov' for reference in item.references)
        assert d.GuidanceArticle.model_validate(client.get('/api/v1/guidance/' + item.slug).json()) == item
        assert all(slug in {hazard.slug for hazard in hazards()} for slug in item.hazard_slugs)


@pytest.mark.parametrize('path,total', [('hazards', 5), ('guidance', 6)])
def test_pagination_and_detached_catalog(path, total, client):
    full = client.get('/api/v1/' + path).json()['items']
    page = client.get('/api/v1/' + path, params={'limit': 2, 'offset': 1}).json()
    assert page == {'items': full[1:3], 'total': total, 'offset': 1, 'limit': 2}
    assert client.get('/api/v1/' + path, params={'offset': 100}).json()['items'] == []
    records = hazards() if path == 'hazards' else guidance()
    records[0].references.clear()
    assert client.get('/api/v1/' + path).json()['items'][0]['references']


def test_guidance_filters_match_declared_metadata_without_hazard_inference(client):
    response = client.get('/api/v1/guidance?indicator=spo2').json()
    assert [item['slug'] for item in response['items']] == ['environmental_monitoring']
    assert client.get('/api/v1/guidance?indicator=heart_rate&hazard=space_radiation').json()['total'] == 0
    assert client.get('/api/v1/guidance?hazard=unknown').json()['total'] == 0
    assert client.get('/api/v1/guidance?indicator=sleep_hours').status_code == 422


@pytest.mark.parametrize('path', ['/hazards/not-real', '/guidance/not-real'])
def test_missing_catalog_resource_uses_existing_error_envelope(client, path):
    response = client.get('/api/v1' + path)
    assert response.status_code == 404 and response.json()['error']['code'] == 'not_found'


@pytest.mark.parametrize('path', ['/hazards?limit=0', '/guidance?offset=-1', '/guidance?limit=1001'])
def test_catalog_query_validation(client, path):
    assert client.get('/api/v1' + path).status_code == 422


def test_all_education_gets_leave_every_repository_unchanged(client):
    before = deepcopy(client.app.state.adapter._state)
    for path in ['/hazards', '/guidance', '/hazards/space_radiation', '/guidance/sleep_circadian', '/guidance?indicator=spo2']:
        assert client.get('/api/v1' + path).status_code == 200
    assert client.app.state.adapter._state == before
    assert client.post('/api/v1/guidance', json={}).status_code == 405
