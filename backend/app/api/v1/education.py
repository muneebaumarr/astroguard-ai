from fastapi import APIRouter
from astroguard_contracts import dto as d
from astroguard_contracts.enums import HealthIndicator, EnvironmentalIndicator
from app.services.education import hazards, guidance
from app.services.errors import ResourceNotFound
from .routes import Limit, Offset

router = APIRouter()


@router.get('/hazards', response_model=d.Page[d.Hazard])
def list_hazards(limit: Limit = 100, offset: Offset = 0):
    values = hazards()
    return d.Page[d.Hazard](items=values[offset:offset + limit], total=len(values), limit=limit, offset=offset)


@router.get('/hazards/{slug}', response_model=d.Hazard)
def get_hazard(slug: str):
    result = next((item for item in hazards() if item.slug == slug), None)
    if result is None:
        raise ResourceNotFound('Hazard not found')
    return result


@router.get('/guidance', response_model=d.Page[d.GuidanceArticle])
def list_guidance(limit: Limit = 100, offset: Offset = 0,
                  indicator: HealthIndicator | EnvironmentalIndicator | None = None, hazard: str | None = None):
    values = [item for item in guidance() if (indicator is None or indicator in item.indicators)
        and (hazard is None or hazard in item.hazard_slugs)]
    return d.Page[d.GuidanceArticle](items=values[offset:offset + limit], total=len(values), limit=limit, offset=offset)


@router.get('/guidance/{slug}', response_model=d.GuidanceArticle)
def get_guidance(slug: str):
    result = next((item for item in guidance() if item.slug == slug), None)
    if result is None:
        raise ResourceNotFound('Guidance article not found')
    return result
