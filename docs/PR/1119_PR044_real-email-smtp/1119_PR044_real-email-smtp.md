# PR44 feat: 인증 메일 실제 발송(SMTP)과 시연 주소 Mailpit 유지

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude), 커밋 3개는 김민호
- 브랜치: `feat/real-email-smtp` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/44
- 관련 이슈: 없음
- 관련 설계: 해당 없음(설계 문서에 메일 발송 항목 없음)
- 작업 설계: [docs/work/feat/real-email-smtp/1119_real-email-smtp.md](../../work/feat/real-email-smtp/1119_real-email-smtp.md)

## 목적

배포 서버의 인증 코드 메일을 가입하는 사람의 실제 메일함으로 보낸다. 시연 계정(`@dongle-demo.ac.kr`)과 시연용 새 가입 주소(`@guest-demo.ac.kr`)는 실제로 없는 주소라서, 이 주소로 가는 메일만 계속 Mailpit으로 보낸다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 배포 | `compose.yaml` | (김민호) `api`·`notifier`·`demo-seed`의 `EMAIL_HOST`·`EMAIL_PORT`를 `${EMAIL_HOST:-mailpit}`·`${EMAIL_PORT:-1025}`로 받는다. 플랫폼 환경변수가 없으면 지금처럼 Mailpit |
| 배포 | `compose.yaml` | `api`에 `DEMO_EMAIL_HOST: mailpit`, `DEMO_EMAIL_PORT: "1025"` |
| 설정 | `config/settings/prod.py` | (김민호) 메일 설정 주석 |
| 설정 | `config/settings/base.py` | `DEMO_EMAIL_HOST`(기본 빈 값), `DEMO_EMAIL_PORT`(기본 1025), `DEMO_EMAIL_DOMAINS`(기본 `dongle-demo.ac.kr`, `guest-demo.ac.kr`) |
| 인증 | `apps/users/verification.py` | `mail_connection_for(email)`: 받는 주소 도메인이 `DEMO_EMAIL_DOMAINS`와 정확히 같고 `DEMO_EMAIL_HOST`가 있으면 그 SMTP(계정 없음, TLS 끔, 10초) 연결을 만든다. `send_code`가 이 연결로 보낸다. 아니면 기본 설정 |
| 테스트 | `apps/users/tests.py` | `DemoMailRoutingTests` 5개: 시연 도메인 연결 값, 다른 도메인·하위 도메인은 기본, `DEMO_EMAIL_HOST` 비면 기본, 발송 API가 시연 주소는 Mailpit 연결·학교 주소는 기본 연결을 쓰는지 |
| 문서 | `.env.example`, `README.md` | (김민호) 「실제 메일 발송」 절과 Gmail 예시. 시연 주소 Mailpit 설명과 `DEMO_EMAIL_*` 예시 추가 |

## 설계·결정 반영

- 사용자 결정(2026-11-19): 실제 SMTP를 켜되 시연 주소만 Mailpit으로 보낸다.
- 김민호 님 PR41(`ff0caae`, `262e863`, `13567c7`)은 2026-11-18 main에 병합됐다가 2026-11-19 main에서 되돌려졌다. 같은 커밋을 cherry-pick해 작성자를 유지했다.

## 디자인 영향

해당 없음

## 테스트

- `python manage.py test`: sqlite 192개 통과, PostgreSQL 17(docker 임시 컨테이너) 192개 통과.
- `manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .` 통과.
- `docker compose config`: `EMAIL_HOST`를 넣으면 세 서비스 모두 그 값, 빼면 `mailpit`·`1025`. `api`에 `DEMO_EMAIL_HOST: mailpit`.
- 생략: 로컬에서 실제 Gmail 발송(김민호 님이 2026-11-19 로컬에서 확인). 배포 서버 발송은 릴리스 뒤 확인한다.
- 테스트 데이터·계정 변경 없음(report 갱신 없음).

## 리뷰어가 볼 곳

- `apps/users/verification.py` `mail_connection_for`: 도메인은 정확히 일치할 때만 Mailpit으로 보낸다(`a@sub.dongle-demo.ac.kr`는 실제 SMTP).
- QA 계정 도메인 `dongle.ac.kr` 등 다른 테스트 주소는 실제 SMTP로 가서 코드를 받지 못한다. 필요하면 `DEMO_EMAIL_DOMAINS` 환경변수에 더한다.

## 배포·마이그레이션 메모

- 마이그레이션 없음.
- 실제 메일을 보내려면 플랫폼 환경변수 `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`을 넣고 다시 배포한다. 넣지 않으면 동작이 바뀌지 않는다.
- 이 PR 없이 계정·TLS 값만 넣으면 compose가 `EMAIL_HOST`를 Mailpit으로 고정한 채 TLS를 켜서 발송이 모두 실패한다. 환경변수는 이 PR이 main에 들어간 뒤 넣는다.

## 관련 문서

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`, `changes/1119_be_real-email-smtp.md`, `demo/data.md`
