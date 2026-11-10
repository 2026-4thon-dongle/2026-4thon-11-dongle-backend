"""Swagger(drf-spectacular) 문서용 공통 정의. 동작에는 영향이 없다."""

from typing import Any

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer[Any]):
    """config.exceptions.api_exception_handler가 돌려주는 공통 에러 형식."""

    code = serializers.CharField(help_text="에러 코드. 예: VALIDATION_ERROR, NOT_FOUND")
    message = serializers.CharField(help_text="화면에 그대로 보여 줘도 되는 한국어 메시지")
    # 응답 키 이름이 Serializer.errors와 겹친다. 문서 전용이라 검증에 쓰지 않으므로 무시한다.
    errors = serializers.DictField(  # type: ignore[assignment]
        required=False,
        help_text="code가 VALIDATION_ERROR일 때만 내려온다. 필드 이름별 오류 메시지 목록",
    )


def error_response(description: str) -> OpenApiResponse:
    """에러 응답 문서. description에는 이 상태 코드로 나갈 수 있는 code를 적는다."""
    return OpenApiResponse(ErrorSerializer, description=description)
