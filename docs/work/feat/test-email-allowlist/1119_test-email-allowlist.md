# 학교 메일이 아닌 시연용 실제 메일 예외 허용

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude)
- 브랜치: `feat/test-email-allowlist`
- 기준 커밋: `531512c`
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

실제 메일 발송(SMTP)을 시연하려고 팀이 만든 Gmail 주소 두 개로 가입·로그인할 수 있게 한다. 학교 메일(`ac.kr`) 규칙은 그대로 두고, 환경변수에 적은 주소만 예외로 받는다.

## 목표

- 환경변수 `EXTRA_ALLOWED_EMAILS`(쉼표로 구분, 기본 빈 값)에 있는 주소는 `ac.kr`이 아니어도 인증 코드 발송·확인, 가입을 할 수 있다.
- 목록에 없는 `ac.kr`이 아닌 주소는 지금처럼 400 `INVALID_SCHOOL_EMAIL`이다.
- 주소는 대소문자를 구분하지 않는다.

## 범위

- 포함: 설정, `SchoolEmailField` 검사, 테스트, `.env.example`·README.
- 제외: 배포 서버 환경변수 값(플랫폼에서 넣는다. 주소는 저장소에 적지 않는다), 프론트 화면 검사(프론트 레포에서 따로 고친다), 학교 이름 표시(예외 주소는 `school_name`이 `null`이라 마이 페이지에 「인증 완료」만 보인다).

## 참고한 상위 설계

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`·`verify/`·`signup/`의 학교 메일 규칙(AUTH-04).
- 사용자 지시(2026-11-19): 시연용 실제 메일 두 주소만 예외로 허용한다.

## 작업 계획

1. `config/settings/base.py`에 `EXTRA_ALLOWED_EMAILS`.
2. `apps/users/verification.py`에 `is_allowed_email`, `SchoolEmailField`가 이것을 쓴다.
3. 테스트, `.env.example`·README.

## 세부 설계

- `is_allowed_email(email) = is_school_email(email) or email in EXTRA_ALLOWED_EMAILS`. 비교는 소문자로 한다.
- 예외 주소로 보내는 메일은 시연 주소(`DEMO_EMAIL_DOMAINS`)가 아니므로 실제 SMTP로 간다.

## 확인 방법

- 테스트: 목록에 있는 주소의 코드 발송·확인·가입, 대문자 입력, 목록에 없는 Gmail 400.
- sqlite·PostgreSQL 17 전체 테스트, check·ruff·mypy.
- 배포 뒤: 두 주소 코드 발송이 200, 목록에 없는 Gmail은 400.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-19 | 작성 |

## 결정·변경 사항과 남은 일

- 프론트도 `ac.kr`만 통과시키므로 프론트 레포에서 같은 두 주소를 예외로 고친다(사용자 결정).
