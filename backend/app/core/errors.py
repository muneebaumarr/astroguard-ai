import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from astroguard_contracts.dto import ErrorDetail, ErrorResponse
from astroguard_contracts.errors import Conflict, RepositoryUnavailable

logger = logging.getLogger(__name__)


def error_response(request: Request, status: int, code: str, message: str, details=None):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = ErrorResponse(error=ErrorDetail(code=code, message=message,
        details=details or {}, request_id=request_id))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"),
                        headers={"X-Request-ID": request_id})


def install_error_handlers(app: FastAPI):
    @app.middleware("http")
    async def request_identity(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        details = {".".join(map(str, error["loc"])): error["msg"] for error in exc.errors()}
        return error_response(request, 422, "validation_error", "Request validation failed", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict):
        return error_response(request, 409, "conflict", "The operation conflicts with stored data")

    @app.exception_handler(RepositoryUnavailable)
    async def unavailable(request: Request, exc: RepositoryUnavailable):
        return error_response(request, 503, "repository_unavailable", "Repository unavailable")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("Unexpected request failure", exc_info=exc)
        return error_response(request, 500, "internal_error", "An unexpected error occurred")
