"""
Custom HTTP exceptions and global exception handlers for TaskMaster Pro.
All application-level errors are defined here for consistency.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ── Custom exception classes ──────────────────────────────────────────────────

class TaskMasterException(Exception):
    """Base exception for all TaskMaster domain errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or "TASKMASTER_ERROR"
        super().__init__(detail)


class NotFoundException(TaskMasterException):
    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
        )


class UnauthorizedException(TaskMasterException):
    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(TaskMasterException):
    def __init__(self, detail: str = "You do not have permission to perform this action") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN",
        )


class ConflictException(TaskMasterException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
        )


class BadRequestException(TaskMasterException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BAD_REQUEST",
        )


class UnprocessableEntityException(TaskMasterException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="UNPROCESSABLE_ENTITY",
        )


class FileTooLargeException(TaskMasterException):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb} MB",
            error_code="FILE_TOO_LARGE",
        )


class InvalidTokenException(TaskMasterException):
    def __init__(self, detail: str = "Invalid or expired token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="INVALID_TOKEN",
        )


# ── Exception handlers ────────────────────────────────────────────────────────

def _error_response(status_code: int, detail: str, error_code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "detail": detail,
        },
    )


async def taskmaster_exception_handler(
    request: Request, exc: TaskMasterException
) -> JSONResponse:
    return _error_response(exc.status_code, exc.detail, exc.error_code)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected internal server error occurred",
        error_code="INTERNAL_SERVER_ERROR",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application."""
    app.add_exception_handler(TaskMasterException, taskmaster_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)
