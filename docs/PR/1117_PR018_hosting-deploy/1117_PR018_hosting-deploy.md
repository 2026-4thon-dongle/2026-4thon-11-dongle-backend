# PR18 chore: 홈서버(TwoMES Hosting) 배포 구성

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `chore/hosting-deploy` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/18
- 관련 이슈: 해당 없음
- 관련 설계: TwoMES Hosting 앱 저장소 규칙(`platform_rules`)
- 작업 설계: [docs/work/chore/hosting-deploy/1115_hosting-deploy.md](../../work/chore/hosting-deploy/1115_hosting-deploy.md)

## 목적

프론트가 붙을 수 있는 상시 API 서버를 홈서버에 띄우는 배포 구성을 `dev`에 들인다. 배포 서버는 2026-11-16부터 이 브랜치로 돌고 있고, 이 브랜치에 쌓아 병합한 [PR16](../1117_PR016_letter-api-feedback/1117_PR016_letter-api-feedback.md)(스티커 `scale`, 응답 시각 한국 시간, 보낸 편지 `is_read`)도 함께 들어간다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 의존성 | `requirements.txt` | gunicorn, whitenoise 추가 |
| 설정 | `config/settings/base.py`, `prod.py`, `config/urls.py`, `.env.example` | whitenoise 정적 파일, `MEDIA_ROOT` 환경변수, `SERVE_MEDIA`일 때 `/media/` 서빙, `CSRF_TRUSTED_ORIGINS` |
| 배포 | `Dockerfile`, `.dockerignore`, `compose.yaml` | 서비스 `db`(postgres:17), `mailpit`, `init-media`, `api`(gunicorn, 시작 때 `migrate`), `notifier`(60초마다 `notify_arrived_letters`). 호스트 포트 없음, 데이터는 `${HOSTING_DATA_DIR}` |
| 문서 | `README.md`, `CLAUDE.md`, 작업 설계 | 「홈서버 배포」 절, 현재 단계 갱신 |
| PR16 | `apps/letters/`, `config/renderers.py` | PR16 설명서 참고 |

## 설계·결정 반영

- 원격 `dev`가 PR #15 병합 후 자동 삭제돼 `main`(`3fe3d8a`)에서 분기했다. 2026-11-17 사용자 결정으로 `dev`를 `main`(`3fe3d8a`)에서 다시 만들고 이 PR의 대상으로 삼았다.
- 병합 후 배포 서버(`dongle-api`)가 따라갈 브랜치는 `dev`로 한다(사용자 결정). 시연 직전에 `main`으로 바꿀 수 있다.
- `/media/`는 Django `serve`로 준다(가정, 시연 규모). Mailpit 웹 화면은 비밀번호 없이 연다(사용자 결정).

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite, `DATABASE_URL` 지정), 2026-11-17 `9debc4e` 기준: `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 137개 통과.
- 로컬 docker(2026-11-16): 5개 서비스가 healthy로 뜨고 Swagger·정적 파일·미디어·잘못된 Host 거절 확인. PostgreSQL 전체 테스트는 PR16 이전 기준 133개 중 132개 통과(나머지는 PR16에서 고친 시간 의존 테스트). PR16 이후 PostgreSQL 재실행은 생략했다(후속 품질 점검에서 돌린다).
- 배포 서버(배포 #43, `9debc4e`): 임시 계정 3개로 가입 → 일기 → 편지 2통을 보내 `created_at`·`sent_at`·`arrives_at`이 `+09:00`, 데모 모드 1분, 스티커 `scale` 0.3 저장, `scale` 0.9 거절(`400 VALIDATION_ERROR`), 보낸 편지 상세 `is_read=false`를 확인하고 계정을 탈퇴로 지웠다.
- 원격 CI는 없다. 테스트 데이터·계정 문서 변경 없음.

## 리뷰어가 볼 곳

- `compose.yaml`: 서비스 의존 순서와 `notifier` 반복 방식
- `config/urls.py`: `SERVE_MEDIA`일 때만 `/media/`를 붙이는 부분

## 배포·마이그레이션 메모

- 새 마이그레이션 없음.
- 병합하면 저장소 설정(병합 후 브랜치 자동 삭제) 때문에 `chore/hosting-deploy`가 지워진다. 배포 서버가 이 브랜치를 따라가므로 병합 직후 다음 순서로 바꾼다.
  1. PR18 병합 (지금 돌고 있는 컨테이너는 그대로 유지된다)
  2. `update_app dongle-api {"branch": "dev"}`
  3. `deploy dongle-api` → `wait_deployment`로 성공 확인 → `/api/regions/` 응답 확인
- 환경변수(`SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `LETTER_DEMO_MODE`)는 플랫폼에 있고 바꾸지 않는다.

## 관련 문서

- 문서 레포 `changes/1116_be_hosting-deploy.md`, `requests/1116_be2fe_api-server-open.md`
- 문서 레포 `requests/1115_fe2be_sticker-scale.md`, `requests/1116_fe2be_letter-time-kst.md` (PR16)
