# 인증 메일 실제 발송(SMTP)과 시연 주소 Mailpit 유지

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude)
- 브랜치: `feat/real-email-smtp`
- 기준 커밋: `22fbd69`
- 상태: 리뷰 중
- 관련 PR: [#44](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/44)

## 지금 작업 내용

배포 서버의 인증 메일을 Gmail SMTP로 실제 메일함에 보내고, 시연 계정 주소로 가는 메일만 계속 Mailpit으로 보낸다.

## 목표

- 배포 compose가 플랫폼 환경변수 `EMAIL_HOST`·`EMAIL_PORT`를 받아 실제 SMTP로 보낸다. 넣지 않으면 지금처럼 Mailpit으로 간다.
- 받는 주소의 도메인이 `DEMO_EMAIL_DOMAINS`(기본 `dongle-demo.ac.kr`, `guest-demo.ac.kr`)에 있으면 실제 SMTP를 켜도 `DEMO_EMAIL_HOST`(배포에서는 Mailpit)로 보낸다.
- `DEMO_EMAIL_HOST`가 비어 있으면(로컬 기본) 모든 메일이 기본 메일 설정을 따른다.

## 범위

- 포함: 김민호 님의 `feat/real-email-smtp` 커밋 3개(PR41, 2026-11-19에 main에서 되돌려짐)를 다시 가져오기, 시연 주소 Mailpit 발송, 테스트, `.env.example`·README.
- 제외: 배포 서버 환경변수 설정과 배포(릴리스 뒤 플랫폼에서 한다), 다른 테스트 계정 도메인(`dongle.ac.kr` 등) 처리, 메일 본문 디자인.

## 참고한 상위 설계

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`(요청·응답은 바뀌지 않는다), `changes/1119_be_real-email-smtp.md`, `demo/data.md` 「주소와 서버 설정」.
- 백엔드 PR41 `Feat/real email smtp`(커밋 `ff0caae`, `262e863`, `13567c7`).

## 작업 계획

1. PR41 커밋 3개를 작성자를 유지한 채 cherry-pick한다.
2. 설정 `DEMO_EMAIL_HOST`·`DEMO_EMAIL_PORT`·`DEMO_EMAIL_DOMAINS`를 `base.py`에 두고 compose `api`에 `DEMO_EMAIL_HOST: mailpit`을 넣는다.
3. `apps/users/verification.py`가 받는 주소에 맞는 메일 연결을 골라 보낸다.
4. 테스트를 추가하고 `.env.example`·README를 고친다.

## 세부 설계

- 연결 선택: 받는 주소 도메인(소문자)이 `DEMO_EMAIL_DOMAINS`에 정확히 같고 `DEMO_EMAIL_HOST`가 있으면 `django.core.mail.backends.smtp.EmailBackend`를 `host=DEMO_EMAIL_HOST`, `port=DEMO_EMAIL_PORT`, 계정 없음, TLS·SSL 끔, 10초 제한으로 만든다. 그 밖에는 `connection=None`으로 기본 설정을 쓴다.
- 보내는 주소는 같다(`DEFAULT_FROM_EMAIL`). Mailpit은 보내는 주소를 검사하지 않는다.
- 발송 실패 처리(503 `EMAIL_SEND_FAILED`)는 그대로다.

## 확인 방법

- 테스트: 시연 도메인이면 Mailpit 연결로, 다른 도메인이거나 `DEMO_EMAIL_HOST`가 비면 기본 연결로 보내는지.
- sqlite·PostgreSQL 17 전체 테스트, `manage.py check`, ruff, mypy.
- 배포 뒤: 시연 계정 코드가 Mailpit에 오는지, 다른 학교 주소 발송이 200인지.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-19 | 작성. 사용자 결정: 실제 SMTP를 켜되 시연 주소만 Mailpit으로 보낸다 |
| 2026-11-19 | PR41 커밋 3개 cherry-pick(충돌 없음), `DEMO_EMAIL_*` 설정·compose·`mail_connection_for`·테스트 5개·README. sqlite·PostgreSQL 17 테스트 192개, check·ruff·mypy 통과 |

## 결정·변경 사항과 남은 일

- 가정: 브랜치 이름은 PR41과 같은 `feat/real-email-smtp`를 쓴다(원격 브랜치는 PR41 병합 때 지워졌다).
