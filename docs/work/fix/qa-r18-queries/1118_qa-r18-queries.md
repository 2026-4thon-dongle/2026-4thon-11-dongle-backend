# QA 18회차: 목록 API의 N+1 쿼리 줄이기

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r18-queries`
- 기준 커밋: `213bf20`
- 상태: 리뷰 중
- 관련 PR: [PR36](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/36)

## 지금 작업 내용

백엔드 QA 루프 18회차(목록 API 쿼리 수)에서 찾은 N+1을 고친다. 응답 내용은 바꾸지 않는다.

## 목표

- `GET /api/mailbox/conversations/`: 대화 수와 관계없이 쿼리 수가 일정하다. 지금은 대화마다 `is_penpal` 계산(`pair_round_trips`)으로 쿼리가 2개씩 늘고, 페이지를 자르기 전 모든 대화에서 계산해 끝없이 늘어난다(대화 1개 5개 → 8개 19개).
- `GET /api/game/`: 배송 중 편지 수와 관계없이 쿼리 수가 일정하다. 지금은 편지마다 판수·단축 합계를 따로 센다(편지 0통 7개 → 7통 21개).
- `GET /api/diaries/me/`: 일기 수와 관계없이 쿼리 수가 일정하다. 지금은 일기마다 `received_letter_count`를 센다(일기 3개 5개 → 18개 20개).

## 범위

- 포함: `apps/letters/mailbox.py`·`mailbox_views.py`(대화 중 탭), `apps/games/services.py`·`views.py`(게임 홈), `apps/diaries/views.py`·`serializers.py`(내 일기 목록), 쿼리 수 테스트
- 제외: 응답 필드·값 변경, 모델·마이그레이션, 다른 목록(이미 쿼리 수 일정)

## 참고한 상위 설계

- 문서 레포 `api/mailbox.md` 「GET /api/mailbox/conversations/」 `is_penpal`, `api/game.md` 「GET /api/game/」, `api/diaries.md` 「GET /api/diaries/me/」 `received_letter_count`
- 펜팔 기준은 같은 상대와 왕복 3회(대화 여러 개 합산, `apps/letters/services.py` `pair_round_trips`)

## 작업 계획

1. 대화 중 탭: 이미 불러온 대화 목록(편지 prefetch 포함)으로 상대별 왕복 수를 한 번에 세고 `is_penpal`에 쓴다.
2. 게임 홈: 판수(내 판)·단축 합계(두 사람 판)를 편지 묶음으로 두 번만 집계해 `letter_state`에 넘긴다.
3. 내 일기 목록: 도착한 첫 편지 수를 queryset `annotate`로 붙이고 serializer가 있으면 그 값을 쓴다.
4. 데이터를 늘려도 쿼리 수가 같은지 테스트한다.

## 세부 설계

- `mailbox.round_trips_by_partner(views, viewer_id)`: 상대 id → 왕복 수 합계. `pair_round_trips`와 같은 값이다(보이는 대화 = 차단 관계가 아닌 내 대화 전부, 빈 대화는 0).
- `conversation_tab(viewer, now, views=None)`: 이미 만든 `conversation_views`를 받아 다시 조회하지 않는다.
- `games.services.letter_states(user, letters, now)`: `GameRun`을 `letter_id`로 묶어 내 판수와 전체 단축 합계를 각각 한 번에 센다. `letter_state`는 미리 센 값을 받을 수 있게 한다(기본은 지금처럼 직접 셈).
- `MyDiaryListView`: `Count("conversations__letters", filter=Q(is_first=True, arrives_at__lte=now), distinct=True)`를 `received_letters_annotated`로 붙인다. `DiarySerializer.get_received_letter_count`는 이 값이 있으면 쓰고, 없으면 지금처럼 센다(상세·작성 응답).

## 확인 방법

- 테스트: 대화·편지·일기를 늘린 뒤에도 각 목록의 쿼리 수가 늘지 않는다(`assertNumQueries` 대신 늘리기 전후 비교).
- 기존 테스트(값 비교)가 그대로 통과한다.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬(PostgreSQL 17, 시연 데이터 + 상대 15명)에서 쿼리 수 측정 |
| 2026-11-18 | 세 목록 N+1 수정과 쿼리 수 테스트 4개. sqlite·PostgreSQL 176개 통과 |

## 결정·변경 사항과 남은 일

해당 없음
