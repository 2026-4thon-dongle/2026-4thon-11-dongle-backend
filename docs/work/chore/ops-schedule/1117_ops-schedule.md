# 배포 운영 마무리 (주간 글감 알림, 헬스체크, 배포 보안 설정)

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `chore/ops-schedule`
- 기준 커밋: `41f1429` (`feat/demo-seed` 위에 쌓음)
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

홈서버 배포를 시연까지 손 안 대고 돌릴 수 있게 운영 설정을 마무리한다. 주간 글감 알림을 스케줄러에 넣고, Mailpit 헬스체크를 compose에 명시하고, `manage.py check --deploy` 경고를 정리한다.

## 목표

- 배포 서버에서 매주 월요일(한국 시간) 9시 이후 한 시간 안에 주간 글감 알림이 만들어진다. 같은 주에 두 번 만들어지지 않는다.
- 배포 경고 「mailpit: healthcheck 없음」이 없어진다.
- `DJANGO_SETTINGS_MODULE=config.settings.prod`로 `manage.py check --deploy`를 돌리면 경고가 없거나, 남긴 경고에 이유가 적혀 있다.

## 범위

- 포함: `compose.yaml`(`notifier` 반복에 주간 글감 추가, `mailpit` healthcheck), `config/settings/prod.py`(HSTS, SSL 리다이렉트 판단), README 「홈서버 배포」 갱신
- 제외: 백업 일정(플랫폼 설정 `backup_schedule=daily`, `backup_keep=7`로 2026-11-17 설정, 코드 변경 없음), Mailpit 공개 범위 변경(사용자 결정 대기), 실제 메일 서비스 연결(하지 않기로 팀 결정)

## 참고한 상위 설계

- 문서 레포 `api/notifications.md` 주간 글감 알림(SET-05), `create_weekly_prompt_notifications`는 6일 안에 받은 사람에게 다시 만들지 않는다.
- TwoMES Hosting 규칙: 도메인이 붙는 서비스에는 healthcheck를 둔다.

## 작업 계획

1. 작업 설계(이 문서)
2. `notifier`: 60번 반복(약 1시간)마다 한국 시간 월요일 9시 이후인지 보고 `create_weekly_prompt_notifications` 실행
3. `mailpit` healthcheck (`/mailpit readyz`)
4. prod 보안 설정: HSTS, SSL 리다이렉트
5. README, 로컬 compose 확인, PR

## 세부 설계

- 요일·시각 판단은 셸 `date`가 UTC라서 Python `zoneinfo`(`Asia/Seoul`)로 한다. 명령 자체가 6일 안 중복을 막으므로 월요일 9~23시에 여러 번 돌아도 사용자당 한 번이다.
- SSL 리다이렉트: TLS는 Cloudflare 터널에서 끝나고 컨테이너 헬스체크는 `http://127.0.0.1:8000`으로 들어오므로 `SECURE_SSL_REDIRECT`를 켜면 헬스체크가 301을 받는다. 켜지 않고 W008만 이유를 적어 끈다. `zanviq.dev`는 `.dev` 최상위 도메인이라 브라우저가 처음부터 https로만 접속한다(HSTS preload, 추정 아님: `.dev` 전체가 preload 목록에 있다).
- HSTS: 위 이유로 브라우저에는 이미 적용되므로 `SECURE_HSTS_SECONDS`를 환경변수(기본 1일)로 둬 경고를 없앤다. `includeSubDomains`·`preload`는 켜지 않는다.

## 확인 방법

`docker compose config`, 로컬 compose에서 notifier 로그, `manage.py check --deploy`(prod 설정), 배포 후 경고 목록

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-17 | 작업 설계 작성. 플랫폼 백업 일정을 매일·7개 보관으로 설정하고 수동 백업 1회 성공(파일 7.8MB, DB 덤프 24KB) |

## 결정·변경 사항과 남은 일

- Mailpit이 비밀번호 없이 공개돼 있어 누구나 로그인 코드와 받는 사람 메일 주소를 볼 수 있다(2026-11-17 확인). 보호 방법은 사용자 결정 대기.
