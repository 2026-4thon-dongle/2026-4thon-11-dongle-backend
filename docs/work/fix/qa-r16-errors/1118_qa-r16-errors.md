# QA 16회차: 깨진 JSON 본문을 BAD_REQUEST로

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r16-errors`
- 기준 커밋: `213bf20`
- 상태: 리뷰 중
- 관련 PR: [PR35](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/35)

## 지금 작업 내용

백엔드 QA 루프 16회차(입력 검증·에러 형식)에서 찾은 문제를 고친다.

## 목표

- JSON으로 읽을 수 없는 본문을 보내면 400 `BAD_REQUEST`와 한국어 메시지 「요청 형식을 확인해 주세요.」가 나온다. 지금은 400 `PARSE_ERROR`와 영어 메시지(`JSON parse error - Expecting property name ...`)가 나온다.

## 범위

- 포함: 공통 에러 처리기(`config/exceptions.py`)의 DRF `ParseError` 처리, 테스트
- 제외: 415 `UNSUPPORTED_MEDIA_TYPE`, 405 `METHOD_NOT_ALLOWED`(명세 표에 없지만 상태 코드가 달라 문서 보완으로 남긴다)

## 참고한 상위 설계

- 문서 레포 `api/common.md` 「공통 에러 코드」: 400 `BAD_REQUEST` = 요청 자체를 처리할 수 없음(헤더·본문 형식 등). `PARSE_ERROR`는 표에 없다.
- backend PR21에서 Django 수준 400을 `BAD_REQUEST`로 맞췄고, DRF 수준 본문 파싱 오류가 남아 있었다.

## 작업 계획

1. `api_exception_handler`에서 `ParseError`면 `{"code": "BAD_REQUEST", "message": "요청 형식을 확인해 주세요."}`로 바꾼다.
2. 테스트를 추가한다.

## 세부 설계

- 메시지는 Django 수준 `bad_request` 핸들러와 같은 문구를 쓴다(상수로 묶는다).
- 파서 상세(어느 줄 몇 번째 글자인지)는 응답에 넣지 않는다.

## 확인 방법

- `POST /api/diaries/`에 `{"body": "x",`(닫히지 않은 JSON)를 `application/json`으로 보내면 400 `BAD_REQUEST`.
- 공개 API(`POST /api/auth/email/send/`)도 같다.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100)에서 재현: 400 `PARSE_ERROR` + 영어 메시지 |
| 2026-11-18 | ParseError 처리와 테스트 1개. sqlite 173개 통과 |

## 결정·변경 사항과 남은 일

- 415 `UNSUPPORTED_MEDIA_TYPE`, 405 `METHOD_NOT_ALLOWED`, 401 `AUTHENTICATION_FAILED`는 지금도 JSON 형식이지만 `api/common.md` 표에 없다. QA 진행 기록 「문서 수정 필요」에 남긴다.
