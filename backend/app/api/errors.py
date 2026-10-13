"""Consistent JSON error bodies: ``{"code": ..., "detail": ...}``.

Public messages never contain file-system paths, settings or stack traces; the full
exception is logged server-side with the request id.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from analytics.data import DatasetNotFoundError
from analytics.ml import InvalidRecordError, ModelArtifactError, ModelNotAvailableError
from analytics.ml.predict import UnsupportedModelError
from analytics.preprocessing import InvalidDatasetError, LeakageError

log = logging.getLogger("app.errors")

HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def error(status_code: int, code: str, detail: str, request: Request | None = None) -> JSONResponse:
    if request is not None and status_code != 500:
        log.warning(
            "request rejected",
            extra={"code": code, "status": status_code, "path": request.url.path,
                   "request_id": getattr(request.state, "request_id", None)},
        )  # fmt: skip
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DatasetNotFoundError)
    async def dataset_missing(request: Request, exc: DatasetNotFoundError) -> JSONResponse:
        name = exc.public_filename or "A cohort file"
        return error(
            503,
            "dataset_unavailable",
            f"{name} has not been downloaded. Run `python -m analytics.data.download` "
            "from backend/.",
            request,
        )

    @app.exception_handler(InvalidDatasetError)
    async def dataset_invalid(request: Request, exc: InvalidDatasetError) -> JSONResponse:
        return error(503, "dataset_invalid", str(exc), request)

    @app.exception_handler(ModelArtifactError)
    async def models_missing(request: Request, exc: ModelArtifactError) -> JSONResponse:
        return error(503, "models_unavailable", str(exc), request)

    @app.exception_handler(ModelNotAvailableError)
    async def model_not_persisted(request: Request, exc: ModelNotAvailableError) -> JSONResponse:
        return error(404, "model_not_available", str(exc), request)

    @app.exception_handler(InvalidRecordError)
    @app.exception_handler(LeakageError)
    async def invalid_record(request: Request, exc: ValueError) -> JSONResponse:
        return error(422, "invalid_record", str(exc), request)

    @app.exception_handler(UnsupportedModelError)
    async def unsupported_model(request: Request, exc: UnsupportedModelError) -> JSONResponse:
        return error(422, "invalid_request", str(exc), request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item["loc"][1:]) or "request"
            messages.append(f"{location}: {item['msg']}")
        return error(422, "invalid_request", "; ".join(messages), request)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_CODES.get(exc.status_code, "http_error")
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error(exc.status_code, code, detail, request)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        log.error(
            "unhandled error",
            exc_info=exc,
            extra={"path": request.url.path, "request_id": request_id},
        )
        return error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            f"An unexpected error occurred (request {request_id}). It has been logged.",
        )
