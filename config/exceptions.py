"""API 공통 에러 형식. 모든 에러 응답은 {"code", "message", ...}로 돌려준다."""

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApiError(APIException):
    """코드가 정해진 업무 에러. extra는 응답 최상위 필드로 함께 나간다."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **extra: Any,
    ) -> None:
        super().__init__(detail=message, code=code)
        self.status_code = status_code
        self.error_code = code
        self.message = message
        self.extra = extra


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ApiError):
        response.data = {"code": exc.error_code, "message": exc.message, **exc.extra}
    elif isinstance(exc, ValidationError):
        response.data = {
            "code": "VALIDATION_ERROR",
            "message": "입력값을 확인해 주세요.",
            "errors": response.data,
        }
    elif isinstance(exc, APIException):
        detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
        response.data = {"code": str(exc.default_code).upper(), "message": str(detail)}
    return response
