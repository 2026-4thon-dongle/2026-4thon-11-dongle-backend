# 홈서버(TwoMES Hosting) 배포 구성

- 작성일: 2026-11-15
- 작성자: 서재민 (AI 작성)
- 브랜치: `chore/hosting-deploy`
- 기준 커밋: `3fe3d8a`
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

프론트가 API를 붙일 수 있게 백엔드를 홈서버 호스팅 플랫폼(TwoMES Hosting)에 배포한다. 플랫폼은 저장소의 `compose.yaml`을 빌드해 띄우므로, 배포용 파일(Dockerfile, compose)과 `prod` 설정 보완이 필요하다.

## 목표

- 저장소를 플랫폼에 올리면 API 서버, PostgreSQL, Mailpit, 편지 도착 알림 스케줄러가 한 번에 뜬다.
- `DEBUG=False`(`config.settings.prod`)로 돌면서 정적 파일(Swagger·admin)과 업로드 이미지(`/media/`)가 나온다.
- 프론트가 https 주소로 API를 호출하고, 인증 코드를 Mailpit 화면에서 볼 수 있다.

## 범위

- 포함: Dockerfile, `compose.yaml`, `.dockerignore`, gunicorn·whitenoise 추가, prod 설정 보완(정적 파일, 미디어 경로·서빙, CSRF 신뢰 출처), README·CLAUDE.md 갱신, 호스팅 앱 생성·환경변수·도메인 설정
- 제외: 객체 저장소·CDN, 백업 일정, 푸시 알림, 주간 글감 알림 스케줄(`create_weekly_prompt_notifications`)

## 참고한 상위 설계

- TwoMES Hosting 앱 저장소 규칙(`platform_rules`): 호스트 포트·cloudflared·`container_name` 금지, 영구 데이터는 `${HOSTING_DATA_DIR}`, 비밀값은 `.env`가 아니라 플랫폼 환경변수
- 기존 README 「집 서버 시연 설정」(민호님): `DEBUG=True` + runserver 방식. 이 작업은 그 방식을 대체하지 않고, 상시 서버가 필요할 때 쓰는 방법을 추가한다.

## 작업 계획

1. gunicorn, whitenoise 의존성 추가
2. prod 설정 보완 (정적 파일, `MEDIA_ROOT` 환경변수, 미디어 서빙 옵션, `CSRF_TRUSTED_ORIGINS`)
3. Dockerfile, `.dockerignore`
4. `compose.yaml` (db, api, mailpit, notifier, init-media)
5. 로컬 docker 빌드·실행 확인
6. README·CLAUDE.md 갱신
7. 플랫폼에 앱 생성·환경변수·도메인, 배포 확인

## 세부 설계

- 서비스: `db`(postgres:17), `mailpit`, `init-media`(업로드 폴더 소유자를 1000으로 맞추는 한 번짜리), `api`(gunicorn, 시작할 때 `migrate`), `notifier`(60초마다 `notify_arrived_letters`).
- 외부 공개: `api` 8000, `mailpit` 8025만 도메인으로 연다. DB와 SMTP(1025)는 공용 네트워크에 열지 않는다.
- 데이터: DB는 `${HOSTING_DATA_DIR}/postgres`, 업로드 이미지는 `${HOSTING_DATA_DIR}/media`.
- 환경변수 `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `LETTER_DEMO_MODE`는 플랫폼에 넣는다. `DATABASE_URL`, `EMAIL_HOST`, `MEDIA_ROOT`, `SERVE_MEDIA`는 compose가 정한다.
- `/media/`는 Django `serve`로 준다(가정). 시연 규모에서는 충분하고, 트래픽이 늘면 별도 서버로 옮긴다. 사진은 로그인 없이 주소로 열린다는 점은 기존 DEBUG 동작과 같다.
- Mailpit 웹 화면은 비밀번호 없이 연다(사용자 결정). 누구나 인증 코드를 볼 수 있으므로 시연·테스트 기간에만 둔다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`, `docker compose config`, 로컬 `docker compose up`과 배포 후 `/api/regions/`·`/api/docs/`·`/media/` 호출

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-15 | 작업 설계 작성. 원격에 `dev` 브랜치가 없어(PR #15 병합 후 자동 삭제) `main`(`3fe3d8a`)에서 분기. PR 대상은 사용자 결정 대기 |
| 2026-11-16 | gunicorn·whitenoise, prod 설정(정적 파일, `MEDIA_ROOT`, `SERVE_MEDIA`, `CSRF_TRUSTED_ORIGINS`), Dockerfile, `compose.yaml`, README 구현. 로컬 docker로 5개 서비스가 healthy로 뜨는 것과 Swagger·정적 파일·미디어·잘못된 Host 거절을 확인. PostgreSQL에서 테스트 133개 중 132개 통과(나머지 1개 `test_first_letter`는 자정~새벽 시간대에 새벽 우표가 같이 지급돼 실패하는 시간 의존 테스트) |
| 2026-11-16 | 플랫폼에 앱 `dongle-api`(브랜치 `chore/hosting-deploy`, 저장공간 5GB) 생성·배포 성공. 도메인 `dongle-api.zanviq.dev`(api 8000), `dongle-mail.zanviq.dev`(mailpit 8025). 배포 서버에서 인증 메일 → 가입 → 일기+사진 → 이미지 조회 → 탈퇴까지 확인(이미지 URL은 https). CORS 허용(`localhost:5173`)·비허용 출처 동작 확인 |

## 결정·변경 사항과 남은 일

- 원격 `dev`가 사라졌다. PR을 어느 브랜치로 보낼지는 사용자에게 확인한다.
- 플랫폼 앱은 지금 `chore/hosting-deploy` 브랜치를 따라간다. 병합 뒤에는 앱의 브랜치를 `main`(또는 `dev`)으로 바꾼다.
- `LETTER_DEMO_MODE=True`로 배포했다. 실제 배송 시간을 보려면 플랫폼 환경변수를 `False`로 바꾸고 다시 배포한다.
- 시간 의존 테스트: `apps/letters/tests.py` `test_first_letter`가 00시대(새벽 우표 시간)에 실패한다. 별도 수정이 필요하다.
- 남은 일: PR·병합, 앱 브랜치 전환, Mailpit 공개 범위 재검토, 백업 일정.
