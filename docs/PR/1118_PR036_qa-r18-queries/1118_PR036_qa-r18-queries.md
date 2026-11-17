# PR36 perf: 대화 중 탭·게임 홈·내 일기 목록 N+1 쿼리 줄이기 (QA 18회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r18-queries` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/36
- 관련 이슈: 해당 없음 (백엔드 QA 루프 18회차)
- 관련 설계: 문서 레포 `api/mailbox.md`, `api/game.md`, `api/diaries.md`
- 작업 설계: [docs/work/fix/qa-r18-queries/1118_qa-r18-queries.md](../../work/fix/qa-r18-queries/1118_qa-r18-queries.md)

## 목적

목록 API 3개의 N+1 쿼리를 없앤다(응답 변경 없음).

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 우체통 | `apps/letters/mailbox.py`, `mailbox_views.py` | `round_trips_by_partner`로 불러온 대화에서 상대별 왕복 수를 세어 `is_penpal`에 쓴다. `conversation_tab`이 만든 `conversation_views`를 받아 다시 조회하지 않는다 |
| 게임 | `apps/games/services.py`, `views.py` | `letter_states`가 내 판수·단축 합계를 편지 묶음으로 두 번만 센다. `letter_state`는 미리 센 값을 받을 수 있다 |
| 일기 | `apps/diaries/views.py`, `serializers.py` | 내 일기 목록 queryset이 도착한 첫 편지 수를 `annotate`로 함께 세고, serializer는 그 값이 있으면 쓴다(상세·작성은 지금처럼 직접 셈) |
| 테스트 | `config/tests_queries.py` | 상대 1명 → 5명으로 늘려도 세 목록의 쿼리 수가 같은지, 받은 편지 수 값이 그대로인지 4개 |

## 설계·결정 반영

- 응답 필드·값은 바꾸지 않았다. `is_penpal`은 `services.pair_round_trips`와 같은 기준(같은 상대와의 모든 대화 왕복 합계 3 이상)이다.
- `pair_round_trips`는 발송 때 펜팔 우표 지급과 대화 상세에서 그대로 쓴다(한 번 부르는 곳이라 바꾸지 않음).

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 176개 통과(이 PR에서 4개 추가).
- 로컬 PostgreSQL 17(docker `dongle-qa-pg`): 같은 검사와 `manage.py test` 176개 통과.
- 새 테스트를 수정 전 `dev`에 넣으면 3개가 실패한다(대화 중 탭 9→33, 게임 홈 9→17, 내 일기 목록 3→7 쿼리).
- 측정(수정 전, 로컬 PostgreSQL·시연 데이터에 상대 15명 추가): 대화 중 탭 5→19, 게임 홈 7→21, 내 일기 목록 5→20 쿼리. 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `round_trips_by_partner`가 `pair_round_trips`와 같은 값을 내는지(차단 관계 대화는 둘 다 목록에서 빠짐)
- 내 일기 목록 `Count(..., distinct=True)`가 대화·편지 조인에서 중복 없이 세는지

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/mailbox.md`, `api/game.md`, `api/diaries.md`
