# PR10 feat: 우체통·편지 열람·펜팔 친구 API

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/mailbox` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/10
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/mailbox.md`, `spec/mail.md`, `screens/05_mailbox.md`
- 작업 설계: `docs/work/feat/mailbox/1114_mailbox.md`

## 목적

우체통 탭 4개, 편지 열람·봉투 열기·넘기기, 대화 기록, 펜팔 친구를 구현한다(MAIL-01~09).

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 모델 | `apps/users/models.py`, `serializers.py`, `migrations/0003` | `User.avatar`(프로필 고향이 표정, 가입 때 7종 중 무작위). 내 정보 응답에 `avatar` 추가 |
| 기능 | `apps/letters/mailbox.py` | 대화 상태 계산(my_turn / in_transit / waiting / closed), 탭별 조회, 보관, 펜팔, `can_reply`·`can_pass` |
| API | `apps/letters/mailbox_views.py`, `mailbox_serializers.py`, `mailbox_urls.py` | `GET /api/mailbox/summary/`, `new/`, `conversations/`, `conversations/{id}/`, `in-transit/`, `archive/`, `GET /api/letters/{id}/`, `POST /api/letters/{id}/open/`, `POST /api/letters/{id}/pass/`, `GET /api/penpals/` |
| 설정 | `config/urls.py`, `config/settings/base.py`, `apps/letters/urls.py` | URL 등록, Swagger 「우체통」 태그 |
| 테스트 | `apps/letters/tests_mailbox.py` | 11개 |

## 설계·결정 반영

- 문서 레포 `api/mailbox.md`의 경로·필드·에러 코드대로 구현했다.
- 대화 중 탭은 첫 편지를 보낸 사람에게는 보낸 순간부터, 받은 사람에게는 답장한 뒤부터 나온다. 명세의 「첫 왕복이 시작된 대화」를 보낸 사람 쪽에서는 첫 편지부터로 해석했다(가정, 5-3의 「답장 기다리는 중」 카드가 이 경우).
- 넘기기는 넘긴 사람에게만 마무리로 보인다. 상대는 7일 뒤 마무리로 본다(알리지 않기 위해, 가정).
- 마무리 7일, 펜팔 왕복 3회, 프로필 무작위 고정은 문서 레포 요청 2·3·11번의 「현재 가정」이다.
- 차단 관계의 대화·편지는 목록·상세에서 모두 빠진다(가정).
- Swagger enum 이름 충돌을 피하려고 `direction`, `kind`는 문자열 필드로 문서화했다. 값은 명세와 같다.

## 디자인 영향

해당 없음

## 테스트

`feat/mailbox` 위에서 로컬로 돌렸다. DB는 `DATABASE_URL=sqlite:///...`로 바꿔 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 101개 통과 (새로 11개)
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- `python manage.py spectacular`: 경고·에러 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `mailbox.conversation_status`, `in_conversation_tab`: 화면 5-3 상태와 맞는지.
- 대화 목록은 사용자별로 파이썬에서 정렬한 뒤 페이지를 나눈다. 해커톤 규모에서는 충분하지만 대화가 아주 많아지면 쿼리로 옮겨야 한다.

## 배포·마이그레이션 메모

- `users 0003`: `avatar` 추가. 기존 사용자는 마이그레이션 때 하나의 표정이 함께 채워진다.

## 관련 문서

- 문서 레포 `api/mailbox.md`, `spec/mail.md`, `screens/05_mailbox.md`, `requests/1110_be2fe_spec-open-questions.md`
