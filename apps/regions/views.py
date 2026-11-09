from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Region
from .serializers import RegionTreeSerializer


class RegionListView(generics.ListAPIView[Region]):
    """가입 전에도 지역을 고를 수 있어야 하므로 공개한다."""

    permission_classes = [AllowAny]
    serializer_class = RegionTreeSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Region]:
        return Region.objects.filter(parent__isnull=True).prefetch_related(
            "children", "children__parent"
        )
