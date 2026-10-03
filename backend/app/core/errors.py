"""
Standardized error handling and exception definitions for VendorIQ.
Follows Section 27 of VendorIQ PRD:
{
    "error": {
        "code": "...",
        "message": "...",
        "details": null
    }
}
"""
import logging
from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("vendoriq.errors")


def format_error_response(code: str, message: str, details: Optional[Any] = None) -> dict:
    """Formats an API error response adhering to VendorIQ PRD Section 27."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


class AppException(Exception):
    """Base exception for all application-specific errors."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict detected", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class FileTooLargeError(AppException):
    def __init__(self, message: str = "Uploaded file exceeds maximum allowed size", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class InternalError(AppException):
    def __init__(self, message: str = "An unexpected error occurred", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=format_error_response(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Map common status codes to PRD codes
        code_mapping = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "FILE_TOO_LARGE",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_ERROR",
        }
        code = code_mapping.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(
                code=code,
                message=message,
                details=None,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log stack trace internally without exposing it to the client
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected internal server error occurred",
                details=None,
            ),
        )
