# API 에러 형식·일기 노출 점검 결과 수정

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/api-error-visibility`
- 기준 커밋: `a77d5bc`
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

2026-11-17 API 점검(권한·에러 형식)에서 확인된 문제 중 사용자가 고르기로 한 4가지를 고친다.

1. 대화 상세(`GET /api/mailbox/conversations/{id}/`)가 비공개로 바뀌었거나 숨겨진 일기의 `body_preview`를 계속 보여 준다.
2. `?region=²`처럼 유니코드 숫자나 아주 큰 수를 쿼리로 보내면 500이 나고 HTML 페이지가 돌아간다. 없는 `/api/` 경로(404), 요청 크기 초과(400), 처리되지 않은 예외(500)도 HTML이다.
3. `get_object_or_404`가 내는 404의 `message`가 영어다(「No Diary matches the given query.」).
4. 공개 API(인증 메일, 닉네임 확인, 가입, 지역 목록)에 만료된 토큰을 붙이면 401이 난다.

## 목표

- 대화 상세의 `diary`는 보는 사람이 `Diary.objects.visible_to`로 볼 수 있는 일기일 때만 내려가고, 아니면 `null`이다(지운 일기와 같다).
- `/api/` 아래의 모든 에러 응답이 `{"code", "message"}` JSON이다. 숫자 쿼리 값이 잘못되면 400 `VALIDATION_ERROR`다.
- 404 `NOT_FOUND`의 `message`는 한국어다.
- 공개 API는 `Authorization` 헤더를 무시한다.

## 범위

- 포함: `config/exceptions.py`(404 메시지, JSON 404/400/500 핸들러), `config/urls.py`(핸들러 등록), 숫자 쿼리 파싱 함수와 그 사용처 3곳, 대화 상세, 공개 뷰 5개, 테스트, 문서 레포 `api/common.md`·`api/mailbox.md`
- 제외: 점검에서 나온 나머지(직접 만든 `VALIDATION_ERROR`의 `errors` 누락, `AUTHENTICATION_FAILED` 코드, 신고·차단 대상 id 존재 여부 노출), Mailpit 공개(사용자 결정으로 유지)

## 참고한 상위 설계

- 문서 레포 `api/common.md` 에러 형식·공통 에러 코드, `spec/diary.md`(남의 일기 조회는 `visible_to`), `spec/feed.md`(숨김 일기는 404)

## 작업 계획

1. 작업 설계, PR 설명서
2. 문서 레포 `api/common.md`(새 공통 코드), `api/mailbox.md`(대화 상세 `diary`) 초안
3. 대화 상세 `visible_to`
4. 숫자 쿼리 파싱
5. 에러 핸들러(404 한국어, JSON 404/400/500)
6. 공개 뷰 `authentication_classes = []`
7. 테스트, 검사, PR

## 세부 설계

- 숫자 쿼리: `config/params.py`의 `parse_id(value)`가 ASCII 숫자이고 1 이상 2147483647 이하일 때만 `int`를 돌려준다(PostgreSQL `integer` 범위). 나머지는 `None`.
- JSON 핸들러는 경로가 `/api/`로 시작할 때만 JSON을 주고, admin 등 나머지는 Django 기본 화면을 쓴다.
  - 404 `NOT_FOUND` 「요청한 대상을 찾을 수 없습니다.」
  - 400 `BAD_REQUEST` 「요청 형식을 확인해 주세요.」, 요청 크기 초과(`RequestDataTooBig`)는 413 `REQUEST_TOO_LARGE`
  - 500 `SERVER_ERROR` 「잠시 후 다시 시도해 주세요.」
- 새 코드 3개(`BAD_REQUEST`, `REQUEST_TOO_LARGE`, `SERVER_ERROR`)는 `api/common.md` 공통 에러 코드 표에 추가한다. 기존 응답을 바꾸지 않는 추가라 breaking이 아니다(가정: 프론트는 HTML 에러를 이미 코드 없이 처리하고 있다).

## 확인 방법

새 테스트(`config/tests.py`, 각 앱 테스트), 전체 검사, PostgreSQL 테스트, 배포 후 `GET /api/nope/`·`?region=²` 확인

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-17 | 작업 설계 작성. `dev`(`a77d5bc`)에서 분기 |

## 결정·변경 사항과 남은 일

해당 없음
