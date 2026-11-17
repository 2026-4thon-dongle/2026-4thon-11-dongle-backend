from typing import Any

from rest_framework import serializers

from apps.regions.serializers import RegionWithSidoSerializer
from apps.stamps.serializers import RewardSerializer, StampSerializer, UserBriefSerializer


class StarRuleSerializer(serializers.Serializer[Any]):
    stars = serializers.IntegerField()
    min_piece_ratio = serializers.FloatField(help_text="주워야 하는 우표 조각 비율")
    max_hits = serializers.IntegerField(allow_null=True, help_text="허용 부딪힘 수. null이면 무관")
    reduce_seconds = serializers.IntegerField(help_text="이 별로 줄어드는 도착 시간(초)")


class RulesSerializer(serializers.Serializer[Any]):
    run_seconds = serializers.IntegerField(help_text="한 판 길이(초)")
    lanes = serializers.IntegerField(help_text="레인 수")
    plays_per_letter = serializers.IntegerField(help_text="한 사람이 한 편지로 할 수 있는 판수")
    daily_limit = serializers.IntegerField(help_text="하루 판수 (연습 포함)")
    max_reduce_ratio = serializers.FloatField(
        help_text="한 편지에서 줄일 수 있는 비율(배송 시간 대비)"
    )
    min_remaining_seconds = serializers.IntegerField(
        help_text="시작하려면 남아야 하는 도착까지 시간"
    )
    stars = StarRuleSerializer(many=True, help_text="별 기준. 위에서부터 먼저 맞는 것")


class TodaySerializer(serializers.Serializer[Any]):
    played = serializers.IntegerField(help_text="오늘 시작한 판수")
    limit = serializers.IntegerField()
    remaining = serializers.IntegerField()


class ProgressSerializer(serializers.Serializer[Any]):
    plays = serializers.IntegerField(help_text="끝낸 판수")
    successes = serializers.IntegerField(help_text="별 1개 이상 판수")
    three_stars = serializers.IntegerField(help_text="별 3개 판수")
    far_three_stars = serializers.IntegerField(help_text="12시간 거리 편지로 별 3개 판수")
    perfects = serializers.IntegerField(help_text="조각을 모두 줍고 안 부딪힌 판수")
    best_stars = serializers.IntegerField(help_text="최고 별 수")


class GoalSerializer(serializers.Serializer[Any]):
    stamp = StampSerializer(help_text="받을 꾸미기 우표")
    condition = serializers.CharField(help_text="게임 조건 문구")
    target = serializers.IntegerField()
    progress = serializers.IntegerField(help_text="지금까지 (target을 넘지 않음)")
    owned = serializers.BooleanField(help_text="이미 가진 우표인지")


class LetterGameStateSerializer(serializers.Serializer[Any]):
    playable = serializers.BooleanField()
    reason = serializers.CharField(
        allow_null=True,
        help_text="못 할 때 이유 code: LETTER_ARRIVED / ARRIVING_SOON / PLAY_LIMIT / REDUCE_LIMIT",
    )
    remaining_seconds = serializers.IntegerField(help_text="도착까지 남은 시간(초)")
    plays_used = serializers.IntegerField(help_text="내가 이 편지로 시작한 판수")
    plays_left = serializers.IntegerField()
    reduced_seconds = serializers.IntegerField(help_text="이 편지에서 이미 줄인 시간(두 사람 합산)")
    max_reduce_seconds = serializers.IntegerField(help_text="이 편지에서 줄일 수 있는 총시간")
    reducible_seconds = serializers.IntegerField(help_text="지금 더 줄일 수 있는 시간")


class GameLetterSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    direction = serializers.ChoiceField(
        ["sent", "incoming"], help_text="sent: 내가 보냄 / incoming: 나에게 옴"
    )
    partner = UserBriefSerializer(help_text="상대 (발송 시점 닉네임)")
    from_region = RegionWithSidoSerializer()
    to_region = RegionWithSidoSerializer()
    band = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    sent_at = serializers.DateTimeField()
    arrives_at = serializers.DateTimeField()
    game = LetterGameStateSerializer()


class GameHomeSerializer(serializers.Serializer[Any]):
    rules = RulesSerializer()
    today = TodaySerializer()
    progress = ProgressSerializer()
    goals = GoalSerializer(many=True, help_text="꾸미기 우표 8종의 게임 조건")
    letters = GameLetterSerializer(many=True, help_text="배송 중인 내 편지 (도착 임박순)")


class RunStartSerializer(serializers.Serializer[Any]):
    letter_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="배달할 편지 id. 없으면 연습"
    )


class CourseItemSerializer(serializers.Serializer[Any]):
    kind = serializers.CharField(help_text="piece: 우표 조각 / puddle: 물웅덩이")
    lane = serializers.IntegerField(help_text="0~2 (왼쪽부터)")
    t = serializers.FloatField(help_text="시작 뒤 고향이 앞을 지나가는 시각(초)")


class RunSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    letter_id = serializers.IntegerField(allow_null=True)
    practice = serializers.BooleanField(help_text="연습이면 도착 시간을 줄이지 않는다")
    seed = serializers.IntegerField()
    run_seconds = serializers.IntegerField()
    lanes = serializers.IntegerField()
    course = CourseItemSerializer(many=True)
    piece_total = serializers.IntegerField()
    puddle_total = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(help_text="이 시각이 지나면 결과를 받지 않는다")
    reducible_seconds = serializers.IntegerField(help_text="이번 판으로 줄일 수 있는 최대 시간")
    today_remaining = serializers.IntegerField(help_text="이 판을 빼고 오늘 남은 판수")


class RunFinishSerializer(serializers.Serializer[Any]):
    pieces = serializers.IntegerField(min_value=0, help_text="주운 우표 조각 수")
    hits = serializers.IntegerField(min_value=0, help_text="물웅덩이에 부딪힌 수")


class FinishedLetterSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    arrives_at = serializers.DateTimeField(help_text="줄어든 뒤의 도착 시각")
    remaining_seconds = serializers.IntegerField()
    reduced_total_seconds = serializers.IntegerField(help_text="이 편지에서 줄인 총시간")


class RunResultSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    stars = serializers.IntegerField(help_text="0~3. 0이면 배달 실패")
    success = serializers.BooleanField()
    perfect = serializers.BooleanField(help_text="조각을 모두 줍고 안 부딪힘")
    pieces = serializers.IntegerField()
    hits = serializers.IntegerField()
    piece_total = serializers.IntegerField()
    puddle_total = serializers.IntegerField()
    reduced_seconds = serializers.IntegerField(help_text="이번 판으로 줄어든 시간. 연습·실패면 0")
    letter = FinishedLetterSerializer(allow_null=True, help_text="연습이면 null")
    granted_stamps = StampSerializer(many=True, help_text="새로 받은 우표")
    unlocked_rewards = RewardSerializer(many=True, help_text="새로 열린 수집 보상")
    progress = ProgressSerializer()
