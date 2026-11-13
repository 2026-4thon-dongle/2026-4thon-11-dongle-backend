# 설정·알림·글감 Figma 수정 반영

- 작성일: 2026-11-12
- 작성자: 김민호
- 브랜치: `feat/settings-prompt-figma-sync`
- 기준 커밋: `3a94468`
- 상태: 진행 중
- 관련 PR: PR5

## 지금 작업 내용

2026-11-11 Figma 수정으로 문서 레포 `api/users.md`, `api/notifications.md`, `spec/settings.md`, `spec/diary.md`에 「추가 예정」으로 적힌 항목을 백엔드에 구현한다.

## 목표

- `GET/PATCH /api/users/me/settings/`가 `letter_arrival_push_enabled`, `letter_departure_push_enabled`(기본 true)를 읽고 고칠 수 있다.
- 알림 `type`에 `letter_departed`가 있다.
- `GET /api/diaries/prompts/`가 Figma 확정 글감 14개 중에서만 고른다.

## 범위

- 포함: 사용자 설정 필드 2개, 알림 종류 1개, 글감 시드 교체(마이그레이션), 테스트
- 제외: 실제 푸시 발송, `letter_departed` 알림 생성(편지 앱 담당), 토글 값을 발송에 적용하는 일

## 참고한 상위 설계

- 문서 레포 `api/users.md` 「GET/PATCH /api/users/me/settings/」, `api/notifications.md` 알림 종류 표, `spec/settings.md`, `spec/diary.md`, `screens/02_first-diary.md` 「오늘의 글감 목록」, `screens/07_my-page.md` 7-11

## 작업 계획

1. 설정 필드 2개 추가 + 마이그레이션 + 테스트
2. 알림 종류 `letter_departed` 추가 + 마이그레이션
3. 글감 시드 교체 마이그레이션 + 테스트
4. 문서 레포 api·spec의 「추가 예정」 표시 갱신

## 세부 설계

- 기존 글감 8개는 지우지 않고 `is_active=False`로 바꾼다. 주간 글감 알림의 `target_id`가 글감 id를 가리키므로 지우면 끊긴다.
- 「출발」은 나에게 오는 편지가 출발했을 때로 본다(문서 레포 가정 그대로).

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-12 | 작업 설계 작성 |
| 2026-11-12 | 설정 필드 2개, 알림 종류 `letter_departed`, 글감 교체 마이그레이션 구현. check·ruff·mypy·test(62개) 통과 |
| 2026-11-12 | 문서 레포 api/users·notifications·diaries, spec/settings·diary 갱신 |

## 결정·변경 사항과 남은 일

- PR5 설명서 작성: `docs/PR/1113_PR005_settings-prompt-figma-sync/`
