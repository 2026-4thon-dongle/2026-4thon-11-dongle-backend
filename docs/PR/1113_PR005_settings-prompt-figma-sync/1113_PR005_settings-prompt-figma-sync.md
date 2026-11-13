# PR5 feat: 설정·알림·글감 Figma 수정 반영

- 작성일: 2026-11-13
- 작성자: 김민호 (AI 작성)
- 브랜치: `feat/settings-prompt-figma-sync` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/5
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/users.md` 설정 절, `api/notifications.md` 알림 종류 표, `spec/settings.md`, `spec/diary.md`, `screens/02_first-diary.md` 「오늘의 글감 목록」, `screens/07_my-page.md` 7-11
- 작업 설계: `docs/work/feat/settings-prompt-figma-sync/1112_settings-prompt-figma-sync.md`

## 목적

2026-11-11 Figma 수정으로 문서 레포에 「추가 예정」으로 적힌 설정 토글 2개, 알림 종류 1개, 확정 글감 14개를 백엔드에 반영한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 기능 | `apps/users` | `letter_arrival_push_enabled`, `letter_departure_push_enabled`(기본 true) 추가, `GET/PATCH /api/users/me/settings/`에서 읽고 고친다. 마이그레이션 0002 |
| 기능 | `apps/notifications` | 알림 `type`에 `letter_departed` 추가. 마이그레이션 0002 (choices만 변경) |
| 기능 | `apps/diaries` | 글감을 Figma 확정 14개로 교체. 기존 8개는 지우지 않고 `is_active=False`. 마이그레이션 0003 |
| 테스트 | 각 앱 `tests.py` | 설정 필드, 글감 목록 확인 |
| 문서 | `docs/work/...` | 작업 설계와 진행 기록 |

## 설계·결정 반영

- 기존 글감은 주간 글감 알림의 `target_id`가 가리키므로 지우지 않고 비활성화했다.
- 가정: 「출발」 알림은 나에게 오는 편지가 출발했을 때다(문서 레포 가정 그대로).
- 실제 푸시 발송, `letter_departed` 알림 생성(편지 앱 담당), 토글 값을 발송에 적용하는 일은 범위 밖이다.

## 디자인 영향

해당 없음

## 테스트

`feat/settings-prompt-figma-sync`(882e99f) 위에서 로컬로 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 62개 통과
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `apps/diaries/migrations/0003_replace_prompts.py`의 글감 14개 문구가 Figma와 같은지

## 배포·마이그레이션 메모

- 마이그레이션 3개(users 0002, notifications 0002, diaries 0003). users는 컬럼 추가(기본값 있음), notifications는 choices만, diaries는 데이터 마이그레이션이다.
- PR6(`feat/mypage-safety-fe-sync`)이 이 브랜치 위에 쌓여 있어 이 PR을 먼저 병합해야 한다.

## 관련 문서

- 문서 레포 `api/users.md`, `api/notifications.md`, `api/diaries.md`, `spec/settings.md`, `spec/diary.md`
