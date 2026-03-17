import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

ERROR_CODE_UNAUTHORIZED = "UNAUTHORIZED"
ERROR_CODE_FORBIDDEN = "FORBIDDEN"
ERROR_CODE_CONFLICT = "CONFLICT"
ERROR_CODE_BAD_REQUEST = "BAD_REQUEST"
ERROR_CODE_NOT_FOUND = "NOT_FOUND"
ERROR_CODE_INTERNAL = "INTERNAL_ERROR"


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class ConflictError(Exception):
    pass


class RoleError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def _error_body(detail: str, code: str) -> dict[str, str]:
    return {"detail": detail, "code": code}


async def handle_authentication_error(_request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=_error_body(str(exc), ERROR_CODE_UNAUTHORIZED),
    )


async def handle_authorization_error(_request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=_error_body(str(exc), ERROR_CODE_FORBIDDEN),
    )


async def handle_conflict_error(_request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_body(str(exc), ERROR_CODE_CONFLICT),
    )


async def handle_role_error(_request: Request, exc: RoleError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_body(str(exc), ERROR_CODE_BAD_REQUEST),
    )


async def handle_invalid_token(_request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=_error_body(str(exc) or "Invalid or expired token", ERROR_CODE_UNAUTHORIZED),
    )


async def handle_validation_error(_request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_body(str(exc), ERROR_CODE_BAD_REQUEST),
    )


async def handle_not_found_error(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=_error_body(str(exc), ERROR_CODE_NOT_FOUND),
    )


async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            "An unexpected error occurred. Please try again later.",
            ERROR_CODE_INTERNAL,
        ),
    )


async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = ERROR_CODE_INTERNAL
    status_code = exc.status_code
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    if status_code == status.HTTP_401_UNAUTHORIZED:
        code = ERROR_CODE_UNAUTHORIZED
    elif status_code == status.HTTP_403_FORBIDDEN:
        if detail == "Not authenticated":
            status_code = status.HTTP_401_UNAUTHORIZED
            code = ERROR_CODE_UNAUTHORIZED
        else:
            code = ERROR_CODE_FORBIDDEN
    elif status_code == status.HTTP_404_NOT_FOUND:
        code = ERROR_CODE_NOT_FOUND
    elif status_code == status.HTTP_409_CONFLICT:
        code = ERROR_CODE_CONFLICT
    elif 400 <= status_code < 500:
        code = ERROR_CODE_BAD_REQUEST
    return JSONResponse(
        status_code=status_code,
        content=_error_body(detail, code),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(AuthenticationError, handle_authentication_error)  # type: ignore[arg-type]
    app.add_exception_handler(AuthorizationError, handle_authorization_error)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, handle_conflict_error)  # type: ignore[arg-type]
    app.add_exception_handler(RoleError, handle_role_error)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidTokenError, handle_invalid_token)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundError, handle_not_found_error)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected)
