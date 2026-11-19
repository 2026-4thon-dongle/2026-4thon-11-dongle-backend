# PR34 fix(notifications): 주간 글감 알림 target_id에 글감 id 넣기 (QA 12회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r12-notifications` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/34
- 관련 이슈: 해당 없음 (백엔드 QA 루프 12회차)
- 관련 설계: 문서 레포 `api/notifications.md` 개요 표, `spec/diary.md`
- 작업 설계: [docs/work/fix/qa-r12-notifications/1118_qa-r12-notifications.md](../../work/fix/qa-r12-notifications/1118_qa-r12-notifications.md)

## 목적

주간 글감 알림의 `target_id`에 그 주 글감 id를 넣는다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 알림 | `apps/notifications/management/commands/create_weekly_prompt_notifications.py` | `prompt` 알림에 `target_id=prompt.id` |
| 테스트 | `apps/notifications/tests.py` | `test_weekly_prompt_target_is_prompt_id` |

## 설계·결정 반영

- 문서 레포 `api/notifications.md` 개요 표(`prompt` → 글감 id → 6-1)를 따른다. 제목·본문은 그대로다.
- 이미 만들어진 글감 알림(배포 서버)은 고치지 않는다. 다음 실행부터 새 알림에 들어간다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 173개 통과(이 PR에서 1개 추가).
- 재현(수정 전): 로컬 서버(8100, PostgreSQL 17)에서 `create_weekly_prompt_notifications` 실행 뒤 시연1의 `prompt` 알림 `target_id`가 null.
- 중간에 테스트 코드의 mypy 오류(`target_id`가 `int | None`)를 따로 커밋으로 고쳤다.
- PostgreSQL 전체 테스트는 생략(모델·쿼리 변경 없음). 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- 명령의 `Notification(...)`에 `target_id`만 더했는지

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. `notifier` 서비스가 월요일 9시 이후 이 명령을 부른다. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/notifications.md` 개요 표, `spec/diary.md`
