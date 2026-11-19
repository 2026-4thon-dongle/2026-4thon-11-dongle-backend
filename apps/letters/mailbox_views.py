from datetime import datetime
from typing import Any, cast

from django.db.models import F, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diaries.models import Diary
from apps.moderations.services import blocked_user_ids
from apps.regions.serializers import RegionWithSidoSerializer
from apps.users.models import User
from config.exceptions import ApiError
from config.params import parse_id
from config.schema import error_response

from .mailbox import (
    MY_TURN,
    ConversationView,
    archive_items,
    can_pass,
    can_reply,
    conversation_tab,
    conversation_views,
    get_conversation_view,
    in_transit_letters,
    new_letters,
    penpals,
    preview,
    round_trips_by_partner,
)
from .mailbox_serializers import (
    ArchiveItemSerializer,
    ConversationDetailSerializer,
    ConversationItemSerializer,
    InTransitSerializer,
    LetterDetailSerializer,
    NewLetterSerializer,
    PartnerSerializer,
    PenpalSerializer,
    SummarySerializer,
)
from .models import Letter
from .serializers import STICKER_DEFAULT_SCALE
from .services import PENPAL_ROUND_TRIPS, pair_round_trips


def _stamp(letter: Letter) -> dict[str, Any]:
    return {"code": letter.stamp.code, "number": letter.stamp.number, "name": letter.stamp.name}


def _region(region: Any) -> Any:
    return RegionWithSidoSerializer(region).data


def _partner(user: User) -> Any:
    return PartnerSerializer(user).data


def _viewer(request: Request) -> User:
    return cast(User, request.user)


def _is_penpal(view: ConversationView) -> bool:
    c = view.conversation
    return pair_round_trips(c.host_id, c.guest_id) >= PENPAL_ROUND_TRIPS


def _partner_of(view: ConversationView, viewer: User) -> User:
    c = view.conversation
    return c.guest if viewer.pk == c.host_id else c.host


def _last_letter(letter: Letter, viewer: User, now: datetime) -> dict[str, Any]:
    received = letter.recipient_id == viewer.pk
    arrived = letter.has_arrived(now)
    return {
        "id": letter.id,
        "direction": "received" if received else "sent",
        "preview": preview(letter.body) if received and arrived else None,
        "arrived_at": letter.arrives_at if arrived else None,
        "arrives_at": letter.arrives_at,
    }


class MailboxListView(generics.GenericAPIView[Letter]):
    """목록을 리스트로 만든 뒤 공통 페이지네이션(?page=, 20개)을 적용한다."""

    def paginated(self, items: list[Any]) -> Response:
        page = self.paginate_queryset(items)
        assert page is not None
        return self.get_paginated_response(page)


@extend_schema(tags=["우체통"])
class SummaryView(APIView):
    @extend_schema(
        summary="우체통 요약",
        description="우체통 탭의 빨간 점과 개수를 준다 (5-1).",
        responses={200: SummarySerializer},
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        new = new_letters(viewer, now)
        return Response(
            {
                "new_count": new.count(),
                "new_unread_count": new.filter(read_at__isnull=True).count(),
                "my_turn_count": sum(
                    1 for v in conversation_tab(viewer, now) if v.status == MY_TURN
                ),
                "in_transit_count": in_transit_letters(viewer, now).count(),
            }
        )


@extend_schema(tags=["우체통"])
class NewLettersView(MailboxListView):
    @extend_schema(
        summary="새 편지 탭",
        description=(
            "나에게 도착한 첫 편지 중 아직 답장하지 않았고 넘기지 않은 편지 (5-1, MAIL-01).\n\n"
            "- `sido`: 보낸 사람 출발 지역의 시·도 id로 좁힌다.\n"
            "- `ordering`: latest(기본, 도착 최신순) / oldest / unread(안 읽은 것 먼저)."
        ),
        parameters=[
            OpenApiParameter("sido", int, required=False, description="시·도 id"),
            OpenApiParameter("ordering", str, required=False, enum=["latest", "oldest", "unread"]),
            OpenApiParameter("page", int, required=False),
        ],
        responses={
            200: NewLetterSerializer(many=True),
            400: error_response("`VALIDATION_ERROR`: ordering·sido 값이 잘못됨"),
        },
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letters = new_letters(viewer, now)
        raw_sido = request.query_params.get("sido")
        if raw_sido is not None:
            sido = parse_id(raw_sido)
            if sido is None:
                raise ApiError("VALIDATION_ERROR", "sido 값을 확인해 주세요.")
            letters = letters.filter(Q(from_region__parent_id=sido) | Q(from_region_id=sido))
        ordering = request.query_params.get("ordering", "latest")
        orders: dict[str, list[Any]] = {
            "latest": ["-arrives_at", "-id"],
            "oldest": ["arrives_at", "id"],
            "unread": [F("read_at").asc(nulls_first=True), "-arrives_at", "-id"],
        }
        if ordering not in orders:
            raise ApiError("VALIDATION_ERROR", "ordering 값을 확인해 주세요.")
        items = [
            {
                "id": letter.id,
                "sender": _partner(letter.sender),
                "from_region": _region(letter.from_region),
                "diary": {
                    "id": letter.conversation.diary.id,
                    "body_preview": preview(letter.conversation.diary.body),
                }
                if letter.conversation.diary
                else None,
                "duration_minutes": letter.duration_minutes,
                "arrived_at": letter.arrives_at,
                "is_read": letter.read_at is not None,
                "stamp": _stamp(letter),
            }
            for letter in letters.order_by(*orders[ordering])
        ]
        return self.paginated(items)


@extend_schema(tags=["우체통"])
class ConversationListView(MailboxListView):
    @extend_schema(
        summary="대화 중 탭",
        description=(
            "상대별 대화 한 줄 (5-3, MAIL-02). 내가 첫 편지를 보낸 대화는 보낸 순간부터, 받은 "
            "첫 편지에 답장한 대화는 답장한 뒤부터 나온다.\n\n"
            "- status: my_turn(내 차례) / in_transit(배송 중) / waiting(답장 기다리는 중) / "
            "closed(7일 무응답으로 마무리). 이 순서로, 같은 상태 안에서는 최근 편지순.\n"
            "- closed 대화는 보관 탭에도 나온다."
        ),
        parameters=[OpenApiParameter("page", int, required=False)],
        responses={200: ConversationItemSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        # 대화마다 펜팔 여부를 따로 조회하지 않도록 불러온 대화로 상대별 왕복 수를 한 번에 센다
        views = conversation_views(viewer, now)
        trips = round_trips_by_partner(views, viewer.pk)
        items = [
            {
                "id": view.conversation.id,
                "partner": _partner(_partner_of(view, viewer)),
                "status": view.status,
                "round_trips": view.round_trips,
                "is_penpal": trips[view.conversation.partner_of(viewer.pk)] >= PENPAL_ROUND_TRIPS,
                "last_letter": _last_letter(view.latest, viewer, now),
                "closed_at": view.closed_at,
            }
            for view in conversation_tab(viewer, now, views)
        ]
        return self.paginated(items)


@extend_schema(tags=["우체통"])
class ConversationDetailView(APIView):
    @extend_schema(
        summary="주고받은 편지 기록",
        description=(
            "상대와 주고받은 편지 기록 (5-15, MAIL-09). 시작 일기와 편지를 시간순으로 준다. "
            "받은 편지의 미리보기는 도착한 뒤에만 준다. `reply_to`는 지금 답장할 수 있는 편지 id."
        ),
        responses={
            200: ConversationDetailSerializer,
            404: error_response("`NOT_FOUND`: 내 대화가 아님"),
        },
    )
    def get(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        view = get_conversation_view(viewer, pk, now)
        if view is None:
            raise ApiError("NOT_FOUND", "대화를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
        diary = view.conversation.diary
        # 대화가 시작된 뒤 일기가 나만 보기로 바뀌거나 숨겨질 수 있으므로 지금 볼 수 있을 때만 준다
        if diary is not None and not Diary.objects.visible_to(viewer).filter(pk=diary.pk).exists():
            diary = None
        latest = view.latest
        letters = []
        for letter in view.letters:
            arrived = letter.has_arrived(now)
            sent = letter.sender_id == viewer.pk
            letters.append(
                {
                    "id": letter.id,
                    "direction": "sent" if sent else "received",
                    "preview": preview(letter.body) if sent or arrived else None,
                    "stamp": _stamp(letter),
                    "sent_at": letter.sent_at,
                    "arrived_at": letter.arrives_at if arrived else None,
                }
            )
        return Response(
            {
                "id": view.conversation.id,
                "partner": _partner(_partner_of(view, viewer)),
                "status": view.status,
                "round_trips": view.round_trips,
                "is_penpal": _is_penpal(view),
                "letter_count": len(view.letters),
                "diary": {
                    "id": diary.id,
                    "author": {"id": diary.author_id, "nickname": diary.author.nickname},
                    "body_preview": preview(diary.body),
                    "created_at": diary.created_at,
                }
                if diary
                else None,
                "letters": letters,
                "reply_to": latest.id if can_reply(latest, viewer, now) else None,
            }
        )


@extend_schema(tags=["우체통"])
class InTransitView(MailboxListView):
    @extend_schema(
        summary="배송 중 탭",
        description=(
            "내가 보낸 도착 전 편지와 나에게 오는 도착 전 편지를 도착 임박순으로 준다 "
            "(5-5, MAIL-03). 오는 편지는 내용을 주지 않는다."
        ),
        parameters=[
            OpenApiParameter("direction", str, required=False, enum=["sent", "incoming"]),
            OpenApiParameter("page", int, required=False),
        ],
        responses={
            200: InTransitSerializer(many=True),
            400: error_response("`VALIDATION_ERROR`: direction 값이 잘못됨"),
        },
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letters = in_transit_letters(viewer, now)
        direction = request.query_params.get("direction")
        if direction == "sent":
            letters = letters.filter(sender=viewer)
        elif direction == "incoming":
            letters = letters.filter(recipient=viewer)
        elif direction is not None:
            raise ApiError("VALIDATION_ERROR", "direction 값을 확인해 주세요.")
        items = [
            {
                "id": letter.id,
                "direction": "sent" if letter.sender_id == viewer.pk else "incoming",
                "partner": _partner(
                    letter.recipient if letter.sender_id == viewer.pk else letter.sender
                ),
                "from_region": _region(letter.from_region),
                "to_region": _region(letter.to_region),
                "sent_at": letter.sent_at,
                "arrives_at": letter.arrives_at,
                "stamp": _stamp(letter),
            }
            for letter in letters
        ]
        return self.paginated(items)


@extend_schema(tags=["우체통"])
class ArchiveView(MailboxListView):
    @extend_schema(
        summary="보관 탭",
        description=(
            "넘긴 첫 편지와 마무리된 대화를 최신순으로 준다. 읽기만 할 수 있다 (5-7, MAIL-04)."
        ),
        parameters=[OpenApiParameter("page", int, required=False)],
        responses={200: ArchiveItemSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        items = []
        for item in archive_items(viewer, now):
            first = item.view.letters[0]
            items.append(
                {
                    "kind": item.kind,
                    "letter_id": first.id if item.kind == "passed_letter" else None,
                    "conversation_id": item.view.conversation.id,
                    "partner": _partner(_partner_of(item.view, viewer)),
                    "stamp": _stamp(item.view.latest),
                    "archived_at": item.archived_at,
                }
            )
        return self.paginated(items)


def _visible_letter(viewer: User, pk: int) -> Letter:
    blocked = blocked_user_ids(viewer)
    letter = (
        Letter.objects.filter(Q(sender=viewer) | Q(recipient=viewer), id=pk)
        .exclude(sender_id__in=blocked)
        .exclude(recipient_id__in=blocked)
        .select_related(
            "conversation",
            "sender__residence__parent",
            "recipient__residence__parent",
            "from_region__parent",
            "to_region__parent",
            "stamp",
        )
        .first()
    )
    if letter is None:
        raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return letter


def _check_arrived(letter: Letter, viewer: User, now: datetime) -> None:
    if letter.recipient_id == viewer.pk and not letter.has_arrived(now):
        raise ApiError("NOT_ARRIVED", "아직 도착하지 않은 편지예요.", status.HTTP_403_FORBIDDEN)


def letter_detail(letter: Letter, viewer: User, now: datetime, request: Request) -> dict[str, Any]:
    received = letter.recipient_id == viewer.pk
    return {
        "id": letter.id,
        "conversation_id": letter.conversation_id,
        "is_first": letter.is_first,
        "direction": "received" if received else "sent",
        "sender_nickname": letter.sender_nickname,
        "recipient_nickname": letter.recipient_nickname,
        "sender": _partner(letter.sender),
        "recipient": _partner(letter.recipient),
        "from_region": _region(letter.from_region),
        "to_region": _region(letter.to_region),
        "body": letter.body,
        "stationery": letter.stationery,
        "font": letter.font,
        "signature": request.build_absolute_uri(letter.signature.url) if letter.signature else None,
        "stickers": [
            {**sticker, "scale": sticker.get("scale", STICKER_DEFAULT_SCALE)}
            for sticker in letter.stickers
        ],
        "stamp": _stamp(letter),
        "sent_at": letter.sent_at,
        "arrived_at": letter.arrives_at,
        "duration_minutes": letter.duration_minutes,
        "is_read": received and letter.read_at is not None,
        "can_reply": can_reply(letter, viewer, now),
        "can_pass": can_pass(letter, viewer, now),
    }


LETTER_ERRORS = {
    403: error_response("`NOT_ARRIVED`: 아직 도착하지 않은 받은 편지"),
    404: error_response("`NOT_FOUND`: 내가 보내거나 받은 편지가 아님"),
}


@extend_schema(tags=["우체통"])
class LetterDetailView(APIView):
    @extend_schema(
        summary="편지 상세",
        description=(
            "편지 하나를 렌더링에 필요한 값과 함께 준다 (5-9, MAIL-06). 보낸 편지와 도착한 받은 "
            "편지를 볼 수 있다. 읽음 처리는 하지 않는다(봉투 열기 API가 한다)."
        ),
        responses={200: LetterDetailSerializer, **LETTER_ERRORS},
    )
    def get(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letter = _visible_letter(viewer, pk)
        _check_arrived(letter, viewer, now)
        return Response(letter_detail(letter, viewer, now, request))


@extend_schema(tags=["우체통"])
class LetterOpenView(APIView):
    @extend_schema(
        summary="봉투 열기",
        description=(
            "받은 편지를 읽음 처리하고 편지 상세를 준다 (5-8, MAIL-05). 이미 읽은 편지면 읽은 "
            "시각을 바꾸지 않는다. 읽음 여부는 보낸 사람에게 보여 주지 않는다."
        ),
        request=None,
        responses={
            200: LetterDetailSerializer,
            403: LETTER_ERRORS[403],
            404: error_response("`NOT_FOUND`: 내가 받은 편지가 아님"),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letter = _visible_letter(viewer, pk)
        if letter.recipient_id != viewer.pk:
            raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
        _check_arrived(letter, viewer, now)
        if letter.read_at is None:
            letter.read_at = now
            letter.save(update_fields=["read_at"])
        return Response(letter_detail(letter, viewer, now, request))


@extend_schema(tags=["우체통"])
class LetterPassView(APIView):
    @extend_schema(
        summary="편지 넘기기",
        description=(
            "받은 첫 편지를 보관으로 옮긴다 (5-9, MAIL-06). 상대에게 알리지 않는다. 넘긴 편지에는 "
            "답장할 수 없다."
        ),
        request=None,
        responses={
            204: OpenApiResponse(description="넘김 완료"),
            403: LETTER_ERRORS[403],
            404: error_response("`NOT_FOUND`: 내가 받은 편지가 아님"),
            409: error_response("`NOT_PASSABLE`: 첫 편지가 아니거나 이미 답장·넘김"),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letter = _visible_letter(viewer, pk)
        if letter.recipient_id != viewer.pk:
            raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
        _check_arrived(letter, viewer, now)
        if not can_pass(letter, viewer, now):
            raise ApiError("NOT_PASSABLE", "넘길 수 없는 편지예요.", status.HTTP_409_CONFLICT)
        letter.conversation.passed_at = now
        letter.conversation.save(update_fields=["passed_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["우체통"])
class PenpalListView(MailboxListView):
    @extend_schema(
        summary="펜팔 친구",
        description=(
            "같은 상대와 왕복 3회 이상 주고받은 사용자를 최근 편지순으로 준다 (5-14, MAIL-08)."
        ),
        parameters=[OpenApiParameter("page", int, required=False)],
        responses={200: PenpalSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        items = [
            {
                "partner": _partner(p.partner),
                "conversation_id": p.conversation.id,
                "letter_count": p.letter_count,
                "last_letter_at": p.last_letter_at,
            }
            for p in penpals(viewer, now)
        ]
        return self.paginated(items)
