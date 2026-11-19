# PR47 feat: 학교 메일이 아닌 시연용 메일 예외 허용(EXTRA_ALLOWED_EMAILS)

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude)
- 브랜치: `feat/test-email-allowlist` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/47
- 관련 이슈: 없음
- 관련 설계: 해당 없음(학교 메일 규칙은 문서 레포 `api/auth.md`)
- 작업 설계: [docs/work/feat/test-email-allowlist/1119_test-email-allowlist.md](../../work/feat/test-email-allowlist/1119_test-email-allowlist.md)

## 목적

실제 메일 발송(SMTP)을 시연하려고 팀이 만든 Gmail 주소로 가입·로그인할 수 있게 한다. 학교 메일(`ac.kr`) 규칙은 그대로 두고, 배포 서버 환경변수에 적은 주소만 예외로 받는다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 설정 | `config/settings/base.py`, `.env.example` | `EXTRA_ALLOWED_EMAILS`(쉼표로 구분, 소문자로 저장, 기본 빈 목록) |
| 인증 | `apps/users/verification.py`, `apps/users/serializers.py` | `is_allowed_email`: 학교 메일이거나 `EXTRA_ALLOWED_EMAILS`에 있으면 통과. `SchoolEmailField`(코드 발송·확인)가 이것을 쓴다 |
| 테스트 | `apps/users/tests.py` | `ExtraAllowedEmailTests` 3개: 목록 주소(대문자 입력)로 가입·로그인, 목록에 없는 Gmail 400, 목록이 비면 400 |
| 문서 | `README.md` | 「실제 메일 발송」·「홈서버 배포」에 `EXTRA_ALLOWED_EMAILS` 설명 |

## 설계·결정 반영

- 사용자 지시(2026-11-19): 시연용 실제 메일 두 주소만 예외로 허용한다. 주소는 저장소에 적지 않고 배포 서버 환경변수로 넣는다.

## 디자인 영향

해당 없음

## 테스트

- `python manage.py test`: sqlite 195개 통과, PostgreSQL 17(docker 임시 컨테이너) 195개 통과.
- 이 브랜치에 지금 `main`(`e4e1c31`, 김민호 님 새 편지 탭 되돌리기)을 합친 임시 코드로 sqlite 194개 통과(되돌리기에서 테스트 1개가 빠짐).
- `manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .` 통과.
- 생략: 실제 Gmail 주소로 발송. 배포 뒤 배포 서버에서 확인한다.
- 테스트 데이터·계정 변경 없음(report 갱신 없음).

## 리뷰어가 볼 곳

- 예외 주소는 학교 이름이 없어 `GET /api/users/me/`의 `school_name`이 `null`이다. 프론트는 이때 「인증 완료」만 보여 준다.
- 예외 주소는 시연 주소(`DEMO_EMAIL_DOMAINS`)가 아니라서 실제 SMTP로 간다.
- 프론트도 `ac.kr`만 통과시키므로 프론트 레포에서 같은 주소를 예외로 고쳐야 화면에서 쓸 수 있다.

## 배포·마이그레이션 메모

- 마이그레이션 없음.
- 배포 서버 환경변수 `EXTRA_ALLOWED_EMAILS`에 시연용 주소 두 개를 넣는다. 넣지 않으면 동작이 바뀌지 않는다.

## 관련 문서

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`, `POST /api/auth/email/verify/`, `POST /api/auth/signup/`
