"""API 공통 에러 형식. 모든 에러 응답은 {"code", "message", ...}로 돌려준다."""

from typing import Any

from django.core.exceptions import RequestDataTooBig
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.views import defaults
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

NOT_FOUND_MESSAGE = "요청한 대상을 찾을 수 없습니다."

_CODE_BY_STATUS = {
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
}


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
    elif isinstance(exc, Http404):
        # get_object_or_404의 영어 문구("No Diary matches ...")를 그대로 내보내지 않는다
        response.data = {"code": "NOT_FOUND", "message": NOT_FOUND_MESSAGE}
    else:
        # Django PermissionDenied는 DRF가 응답만 바꿔 주므로 APIException이 아닐 수 있다.
        detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
        code = getattr(exc, "default_code", _CODE_BY_STATUS.get(response.status_code, "ERROR"))
        response.data = {"code": str(code).upper(), "message": str(detail)}
    return response


# DRF 밖에서 나는 에러(없는 경로, 요청 크기 초과, 처리되지 않은 예외)도 /api/ 아래에서는 JSON이다.
# config/urls.py의 handler400·handler404·handler500에 등록한다.


def _is_api(request: HttpRequest) -> bool:
    return request.path.startswith("/api/")


def _error(code: str, message: str, status_code: int) -> JsonResponse:
    return JsonResponse(
        {"code": code, "message": message},
        status=status_code,
        json_dumps_params={"ensure_ascii": False},
    )


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    if not _is_api(request):
        return defaults.bad_request(request, exception)
    if isinstance(exception, RequestDataTooBig):
        return _error(
            "REQUEST_TOO_LARGE",
            "요청이 너무 큽니다.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return _error("BAD_REQUEST", "요청 형식을 확인해 주세요.", status.HTTP_400_BAD_REQUEST)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    if not _is_api(request):
        return defaults.page_not_found(request, exception)
    return _error("NOT_FOUND", NOT_FOUND_MESSAGE, status.HTTP_404_NOT_FOUND)


def server_error(request: HttpRequest) -> HttpResponse:
    if not _is_api(request):
        return defaults.server_error(request)
    return _error(
        "SERVER_ERROR",
        "잠시 후 다시 시도해 주세요.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
