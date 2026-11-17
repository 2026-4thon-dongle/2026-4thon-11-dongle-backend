# PR35 fix(config): 깨진 JSON 본문은 400 BAD_REQUEST로 (QA 16회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r16-errors` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/35
- 관련 이슈: 해당 없음 (백엔드 QA 루프 16회차)
- 관련 설계: 문서 레포 `api/common.md` 「공통 에러 코드」
- 작업 설계: [docs/work/fix/qa-r16-errors/1118_qa-r16-errors.md](../../work/fix/qa-r16-errors/1118_qa-r16-errors.md)

## 목적

깨진 JSON 본문의 에러를 명세의 `BAD_REQUEST`로 맞춘다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 에러 | `config/exceptions.py` | DRF `ParseError`를 400 `BAD_REQUEST` 「요청 형식을 확인해 주세요.」로. 같은 문구를 `BAD_REQUEST_MESSAGE` 상수로 묶어 Django 수준 `bad_request`와 같이 쓴다 |
| 테스트 | `config/tests.py` | `test_malformed_json_is_bad_request` (로그인 API·공개 API) |

## 설계·결정 반영

- `api/common.md` 「공통 에러 코드」의 400 `BAD_REQUEST`(헤더·본문 형식)를 따른다. 상태 코드는 그대로 400이고 `code`·`message`만 바뀐다.
- 가정: 프론트는 `PARSE_ERROR`로 분기하지 않는다(명세에 없는 코드였다).
- 범위 밖: 415 `UNSUPPORTED_MEDIA_TYPE`, 405 `METHOD_NOT_ALLOWED`, 401 `AUTHENTICATION_FAILED`는 상태 코드가 달라 그대로 두고, `api/common.md` 표 보완을 QA 진행 기록 「문서 수정 필요」에 남겼다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 173개 통과(이 PR에서 1개 추가).
- 재현(수정 전, 로컬 서버 8100): `POST /api/diaries/`에 `{"body": "x",` → 400 `PARSE_ERROR` 「JSON parse error - Expecting property name ...」.
- PostgreSQL은 생략(모델·쿼리 변경 없음). 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `api_exception_handler`의 `ParseError` 분기가 `ValidationError` 분기와 겹치지 않는지 (`ParseError`는 `ValidationError`의 하위 클래스가 아니다)

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/common.md` 「공통 에러 코드」
