from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from astroguard_contracts import API_PREFIX
from astroguard_contracts.repositories import AdapterFactory

from app.api.v1.routes import router
from app.api.v1.checkins import router as checkin_router
from app.core.config import Settings
from app.core.errors import install_error_handlers
from app.repositories.memory import MemoryAdapterFactory


def create_app(settings: Settings | None = None, adapter: AdapterFactory | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.repository_backend != "memory":
        raise RuntimeError(
            f"REPOSITORY_BACKEND={settings.repository_backend!r} is unavailable in Phase 1. "
            "The database adapter must be supplied by Developer B; no memory fallback is allowed."
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Each application lifespan gets a fresh process-local fixture store.
        app.state.adapter = adapter if adapter is not None else MemoryAdapterFactory()
        try:
            yield
        finally:
            if adapter is None:
                app.state.adapter.close()
            # Caller owns injected adapters and their lifecycle.

    app = FastAPI(title="AstroGuard AI", version="0.1.0", lifespan=lifespan,
        description="Fictional educational prototype with manual check-ins and limited educational review.")
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Idempotency-Key"],
                       expose_headers=["X-Request-ID"])
    app.include_router(router, prefix=API_PREFIX)
    app.include_router(checkin_router, prefix=API_PREFIX)
    return app


app = create_app()
