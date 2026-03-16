import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        status_code = getattr(exc, "status_code", 400)
        error_code = getattr(exc, "error_code", "app_error")
        public_message = getattr(exc, "public_message", "Application error")
        logger.warning(
            "app_error_response status=%s code=%s cause=%s",
            status_code,
            error_code,
            str(exc),
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": error_code, "message": public_message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        serialized_errors = jsonable_encoder(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request payload",
                },
                "detail": serialized_errors,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error cause=%s", str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "Internal server error",
                }
            },
        )
