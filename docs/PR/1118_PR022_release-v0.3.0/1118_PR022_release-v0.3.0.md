# PR22 release: v0.3.0 (2026-11-18)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `dev` → `main`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/22

## 목적

지난 릴리스(PR15, `main` = `3fe3d8a`) 이후 `dev`에 병합된 작업을 `main`으로 올린다. 배포 서버(`dongle-api`)는 이미 `dev`(`e53d62c`, 배포 #50)를 따라가고 있어, 이 병합으로 배포 서버가 바뀌지는 않는다.

- 버전: 앞선 릴리스 PR7·PR15를 v0.1.0·v0.2.0으로 보고 세 번째 릴리스를 v0.3.0으로 정했다(가정. 이전 릴리스에는 버전이 없었다).

## 변경 사항

| PR | 내용 |
|---|---|
| PR16 | 편지 API 피드백: 스티커 `scale`, 응답 시각 한국 시간(`+09:00`), 보낸 편지 `is_read` |
| PR18 | 홈서버 배포: `compose.yaml`(api·db·mailpit·notifier), Dockerfile, prod 설정 |
| PR19 | 시연 데이터 `seed_demo` 명령과 compose `demo-seed`(`DEMO_SEED=true`일 때만) |
| PR20 | 운영 마무리: 월요일 주간 글감 알림, mailpit healthcheck, prod HSTS |
| PR21 | `/api/` 아래 JSON 404·400·413·500, 숫자 쿼리 검증, 대화 상세 일기 노출 범위, 공개 API 토큰 무시 |
| PR17 | 직접 배달 게임 `apps/games`(API 4개, 새 테이블 `games_gamerun`) |
| PR23 | 이 릴리스 설명서 |

- 마이그레이션: `games` 0001(새 테이블만). 배포 서버에는 배포 #50에서 이미 적용됐다.

## 테스트

- `dev`와 같은 코드(PR17 병합 직전 브랜치 `af6f371`, 트리 동일)로 로컬 sqlite·PostgreSQL 17 `manage.py test` 170개 통과, `ruff`·`mypy`·`check`·`makemigrations --check` 통과(2026-11-17).
- 배포 서버(`e53d62c`): 2026-11-18 시연 계정으로 읽기 API 23개 모두 200. 배포 #50 이후 컨테이너 정상.
- 원격 CI 없음. 테스트 데이터 변경 없음.
