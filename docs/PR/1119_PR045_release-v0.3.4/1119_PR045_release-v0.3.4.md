# PR45 release: v0.3.4 (2026-11-19)

- 작성일: 2026-11-19
- 작성자: 서재민 (AI 작성)
- 브랜치: `dev` → `main`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/45

## 목적

배포 서버의 인증 메일을 Gmail SMTP로 실제 메일함에 보내기 위해 PR44를 `main`으로 올린다(사용자 지시). 배포 서버는 `main`을 따라간다.

- 버전: v0.3.3(PR42) 다음이라 v0.3.4로 정했다(가정).
- 김민호 님 PR41(실제 SMTP)은 2026-11-18 `main`에 바로 병합됐다가 2026-11-19 `main`에서 되돌려졌다. 같은 커밋을 PR44로 `dev`를 거쳐 다시 올린다.

## 변경 사항

| PR | 내용 |
|---|---|
| PR44 | compose가 플랫폼 환경변수 `EMAIL_HOST`·`EMAIL_PORT`를 받아 실제 SMTP로 보낸다(없으면 Mailpit). 시연 주소(`@dongle-demo.ac.kr`·`@guest-demo.ac.kr`)는 실제 SMTP를 켜도 Mailpit으로 보낸다(`DEMO_EMAIL_*`) |
| PR46 | 이 릴리스 설명서 |

- 마이그레이션 없음.
- 배포 전에 플랫폼 환경변수 `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`을 넣는다.

## 테스트

- PR44 브랜치(`dev` `22fbd69` 기준)로 로컬 sqlite·PostgreSQL 17 `manage.py test` 192개 통과, `check`·`ruff`·`mypy` 통과, `docker compose config`로 메일 환경변수 치환 확인.
- 배포 뒤 배포 서버에서 시연 계정 코드가 Mailpit에 오는지, 다른 학교 주소 발송이 성공하는지 확인한다.
- 원격 CI 없음.
