# PR21 fix: API 에러 형식 통일과 비공개 일기 노출 수정

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/api-error-visibility` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/21
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/common.md` 에러 형식, `spec/diary.md`(`visible_to`), `api/mailbox.md` 대화 상세
- 작업 설계: [docs/work/fix/api-error-visibility/1117_api-error-visibility.md](../../work/fix/api-error-visibility/1117_api-error-visibility.md)

## 목적

2026-11-17 API 점검에서 확인한 문제 4가지(비공개·숨김 일기 미리보기 노출, HTML 에러 응답, 영어 404 메시지, 공개 API의 만료 토큰 401)를 고친다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 노출 | `apps/letters/mailbox_views.py` `ConversationDetailView` | `diary`는 `Diary.objects.visible_to(viewer)`로 볼 수 있을 때만, 아니면 `null`. 일기 주인은 계속 본다 |
| 에러 | `config/params.py`, `apps/feeds/views.py`, `apps/letters/views.py`(estimate), `apps/letters/mailbox_views.py`(new `sido`) | `parse_id`: ASCII 숫자이고 1~2147483647일 때만 id로 본다. 그 밖은 400 `VALIDATION_ERROR` |
| 에러 | `config/exceptions.py`, `config/urls.py` | `/api/` 아래 404 `NOT_FOUND`, 400 `BAD_REQUEST`, 413 `REQUEST_TOO_LARGE`, 500 `SERVER_ERROR`를 JSON으로. 그 밖의 경로(admin 등)는 Django 기본 화면 |
| 에러 | `config/exceptions.py` | `Http404`(`get_object_or_404`)의 `message`를 「요청한 대상을 찾을 수 없습니다.」로 |
| 인증 | `apps/users/views.py`(메일 발송·확인, 닉네임 확인, 가입), `apps/regions/views.py` | `authentication_classes = []` |
| 테스트 | `config/tests.py` | 9개 |

## 설계·결정 반영

- 문서 레포 `api/common.md`에 공통 코드 3개(`BAD_REQUEST`, `REQUEST_TOO_LARGE`, `SERVER_ERROR`)와 「공개 API는 `Authorization`을 무시」를 추가하고, `api/mailbox.md` 대화 상세 `diary`를 `object/null`로 고친다(함께 푸시, 비 breaking).
- 요청 크기 초과는 Django가 400으로 처리하던 것을 413으로 바꿨다(가정: 이전 응답은 HTML이라 프론트가 코드로 분기할 수 없었으므로 영향 없음).
- 슬래시 없는 경로의 301(APPEND_SLASH), 직접 만든 `VALIDATION_ERROR`의 `errors` 누락, `AUTHENTICATION_FAILED` 코드, 신고·차단 대상 id 노출은 이번 범위에서 뺐다(사용자 선택).

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 152개 통과(이 PR에서 9개 추가).
- 로컬 PostgreSQL 17(docker): `manage.py test` 152개 통과.
- 배포 서버 확인은 병합 후 한다(`GET /api/nope/`, `?region=%C2%B2`).
- 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `config/exceptions.py` 핸들러가 `/api/` 경로만 JSON으로 바꾸는지
- `apps/letters/views.py` estimate의 `diary_id`·`reply_to` 조건

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 병합하면 `dev` 자동 배포로 반영된다.

## 관련 문서

- 문서 레포 `api/common.md`, `api/mailbox.md`
