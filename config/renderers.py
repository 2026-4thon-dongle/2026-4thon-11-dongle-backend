from datetime import datetime
from typing import Any

from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class LocalTimeJSONEncoder(JSONEncoder):
    """aware datetime을 현재 시간대(Asia/Seoul)로 바꿔서 내린다.

    시리얼라이저의 `DateTimeField`는 이미 한국 시간으로 내리지만, 뷰가 `Response`에
    `datetime`을 그대로 담으면 DB·`timezone.now()`의 UTC 값이 `Z`로 나간다.
    인코더에서 한 번에 맞춰 두면 어느 API든 같은 표기가 된다.
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime) and timezone.is_aware(obj):
            obj = timezone.localtime(obj)
        return super().default(obj)


class LocalTimeJSONRenderer(JSONRenderer):
    encoder_class = LocalTimeJSONEncoder
