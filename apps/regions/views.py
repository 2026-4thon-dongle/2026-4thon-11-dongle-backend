from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Region
from .serializers import RegionTreeSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["지역"],
        summary="지역 목록 (시·도 → 시·군·구)",
        description=(
            "시·도 목록과 각 시·도의 시·군·구를 한 번에 돌려준다. 로그인 없이 호출하며 "
            "페이지네이션하지 않는다. 본가 선택 화면은 `can_be_hometown`, 거주 지역 선택 화면은 "
            "`can_be_residence`가 true인 지역만 고를 수 있게 한다."
        ),
    )
)
class RegionListView(generics.ListAPIView[Region]):
    """가입 전에도 지역을 고를 수 있어야 하므로 공개한다."""

    permission_classes = [AllowAny]
    # 공개 API는 Authorization 헤더를 보지 않는다. 만료된 토큰이 붙어도 401을 내지 않는다
    authentication_classes = []
    serializer_class = RegionTreeSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Region]:
        return Region.objects.filter(parent__isnull=True).prefetch_related(
            "children", "children__parent"
        )
