# PR20 chore: 배포 운영 마무리 (주간 글감 알림, 헬스체크, 배포 보안 설정)

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `chore/ops-schedule` → `feat/demo-seed` (PR19 병합 후 `dev`로 바뀐다)
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/20
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/notifications.md` 주간 글감 알림(SET-05), TwoMES Hosting 앱 규칙(healthcheck)
- 작업 설계: [docs/work/chore/ops-schedule/1117_ops-schedule.md](../../work/chore/ops-schedule/1117_ops-schedule.md)

## 목적

배포 서버를 시연까지 손대지 않고 돌릴 수 있게 운영 설정을 마무리한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 배포 | `compose.yaml` `notifier` | 60번 반복(약 1시간)마다 한국 시간 월요일 9시 이후인지 보고 `create_weekly_prompt_notifications` 실행 |
| 배포 | `compose.yaml` `mailpit` | healthcheck `/mailpit readyz` 명시 (배포 경고 「mailpit: healthcheck 없음」 해소) |
| 설정 | `config/settings/prod.py`, `.env.example` | `SECURE_HSTS_SECONDS`(환경변수, 기본 1일). W005·W008·W021은 이유를 주석에 적고 끔 |
| 문서 | `README.md` 「홈서버 배포」 | 글감 스케줄, 백업 일정, 끈 배포 경고 |

플랫폼 설정(코드 아님): 백업 일정 `daily`, 보관 7개 (2026-11-17).

## 설계·결정 반영

- 주간 글감 명령은 6일 안에 받은 사람에게 다시 만들지 않으므로, 월요일 9~23시에 매시간 돌아도 사용자당 한 번이다. 셸 `date`가 UTC라 요일은 Python `zoneinfo`로 판단한다.
- `SECURE_SSL_REDIRECT`는 켜지 않는다. TLS가 Cloudflare 터널에서 끝나고 헬스체크가 http로 들어와 301을 받으면 배포가 실패하기 때문이다. `.dev` 도메인은 브라우저 HSTS preload 대상이라 브라우저 접속은 https다. 브라우저가 아닌 클라이언트는 `http://dongle-api.zanviq.dev`로도 200을 받는다(2026-11-17 확인). 터널 쪽 「항상 HTTPS」 설정은 플랫폼 소관이라 이 PR에서 다루지 않는다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check` 통과, `manage.py test` 143개 통과.
- `config.settings.prod`로 `manage.py check --deploy`: 「no issues (3 silenced)」.
- 로컬 docker compose: 5개 서비스 정상(api·db·mailpit healthy, mailpit healthcheck가 `/mailpit readyz`). `notifier`가 도착 알림을 만들고, 화요일이라 글감 알림은 건너뜀. 요일 조건을 오늘(화요일)로 바꾼 한 번짜리 실행에서 글감 알림 5건 생성, 같은 반복의 다음 회차는 건너뜀, 다시 실행하면 0건(중복 없음).
- 원격 CI 없음. 테스트 데이터 변경 없음.
- 참고: 저장소 루트의 `.env`에 `LETTER_DEMO_MODE=True`가 있으면 편지 시간 테스트 3개가 실패한다(테스트가 환경변수에 영향받음). 이번 변경과 무관하다.

## 리뷰어가 볼 곳

- `compose.yaml` `notifier` 명령의 `$$` 이스케이프와 반복 조건

## 배포·마이그레이션 메모

- 새 마이그레이션 없음. 병합되면 `dev` 자동 배포로 반영된다. 환경변수 추가는 필요 없다(`SECURE_HSTS_SECONDS` 기본 1일).

## 관련 문서

- 문서 레포 `api/notifications.md`
