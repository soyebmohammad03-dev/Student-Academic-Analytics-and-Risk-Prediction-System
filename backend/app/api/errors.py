"""Consistent JSON error bodies: ``{"code": ..., "detail": ...}``."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from analytics.data import DatasetNotFoundError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DatasetNotFoundError)
    async def dataset_missing(_: Request, exc: DatasetNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "dataset_unavailable", "detail": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        messages = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"][1:]) or "request"
            messages.append(f"{location}: {error['msg']}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"code": "invalid_request", "detail": "; ".join(messages)},
        )
