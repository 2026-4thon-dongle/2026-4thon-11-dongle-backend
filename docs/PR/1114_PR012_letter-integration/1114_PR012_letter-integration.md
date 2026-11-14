# PR12 feat: 편지 알림과 기존 기능 연결

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/letter-integration` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/12
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/notifications.md`, `api/users.md`, `api/diaries.md`, `api/moderations.md`, `spec/settings.md`, `spec/safety.md`
- 작업 설계: `docs/work/feat/letter-integration/1114_letter-integration.md`

## 목적

편지 알림(출발·도착·첫 왕복)을 만들고, 편지 앱 전까지 0이나 미지원으로 둔 기존 기능을 편지와 연결한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 모델 | `apps/letters/models.py`, `migrations/0002` | `Letter.arrival_notified_at`(도착 알림을 만든 시각). 이미 도착한 편지는 알림을 만든 것으로 채운다 |
| 기능 | `apps/letters/notifications.py` | `notify_departed`(발송 때 받는 사람에게), `notify_arrived_letters`(도착·첫 왕복 알림, 편지마다 한 번) |
| 명령 | `apps/letters/management/commands/notify_arrived_letters.py` | 1분마다 실행할 도착 알림 명령 |
| 연결 | `apps/letters/services.py`, `apps/notifications/views.py` | 발송 때 출발 알림. 알림 목록·안 읽은 수 조회 때 그 사용자의 도착 알림을 먼저 만든다 |
| 연결 | `apps/users/serializers.py` | 마이 페이지 `stats.letter_count`, `penpal_count` 실제 값 |
| 연결 | `apps/diaries/serializers.py` | `received_letter_count` 실제 값 |
| 연결 | `apps/moderations/views.py`, `serializers.py`, `tests.py` | 받은 편지 신고(`target_type=letter`) |
| 연결 | `apps/users/views.py` | 탈퇴 때 주고받은 편지의 손글씨 이미지 삭제 |
| 문서 | `README.md` | 도착 알림 명령, 데모 모드 |
| 테스트 | `apps/letters/tests_integration.py` | 7개 |

## 설계·결정 반영

- 알림 이동 대상은 문서 레포 `api/notifications.md` 표를 따른다. 출발·도착은 편지 id, 첫 왕복은 대화 id.
- 알림 문구는 화면 3-4를 따른다. 출발 알림 본문에는 「도착까지 약 N시간 걸려요」를 넣었다(가정).
- 첫 왕복 알림은 대화의 첫 답장이 도착했을 때 받는 사람(첫 편지를 보낸 사람)에게만 만든다. 답장한 사람은 발송 때 우표 획득 모달을 본다(가정).
- 편지 알림 토글 2개는 명세(`spec/settings.md`)대로 푸시 발송에만 적용한다. 알림 센터에는 항상 남긴다. 푸시 발송은 아직 없다.
- 차단 관계면 도착 알림을 만들지 않는다(가정).
- `letter_count`는 보낸 편지와 도착한 받은 편지 수, `received_letter_count`는 그 일기로 도착한 첫 편지 수다(배송 중인 편지는 세지 않는다, 가정).
- 편지 신고는 내가 받아서 도착한 편지만 된다. 없거나 대상이 아니면 `TARGET_NOT_FOUND`.
- 탈퇴하면 대화와 편지가 함께 지워져 상대 우체통에서도 사라진다(기존 CASCADE 동작, 설명 문구에 적음).
- `draft_count`와 `letter_location` 알림은 이번 범위에서 빠진다.

## 디자인 영향

해당 없음

## 테스트

`feat/letter-integration` 위에서 로컬로 돌렸다. DB는 `DATABASE_URL=sqlite:///...`로 바꿔 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 124개 통과 (새로 7개, 편지 신고 미지원 테스트 1개를 없는 편지 404 테스트로 바꿈)
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- `python manage.py spectacular`: 경고·에러 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `notify_arrived_letters`: 편지마다 `arrival_notified_at`을 조건부 update로 먼저 차지해서 명령과 조회가 겹쳐도 알림이 한 번만 생긴다.
- 알림 조회 때 도착 처리를 하므로 알림 API가 쓰기를 한다. 스케줄러를 붙인 뒤에도 남겨 둘지 정해야 한다.

## 배포·마이그레이션 메모

- `letters 0002`: `arrival_notified_at` 추가, 이미 도착한 편지는 `arrives_at`으로 채운다(알림 폭주 방지).
- 배포 때 `notify_arrived_letters`를 1분마다 실행하도록 스케줄러에 등록한다.

## 관련 문서

- 문서 레포 `api/notifications.md`, `api/users.md`, `api/diaries.md`, `api/moderations.md`, `spec/settings.md`, `spec/safety.md`, `screens/03_home-feed.md`
