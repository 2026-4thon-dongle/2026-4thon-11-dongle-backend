# PR28 release: v0.3.2 (2026-11-18)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `dev` → `main`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/28

## 목적

지난 릴리스(PR25, `main` = `44bf00d`) 뒤에 `dev`에 들어온 PR27을 `main`으로 올린다. 배포 서버는 `main`을 따라가고 `DEMO_SEED=true`라, 배포되면 시연 데이터가 새 시드로 처음부터 다시 만들어진다(사용자 지시). 지금 시연 데이터는 테스트용이고 마감 전에 최종 데이터로 다시 만든다.

## 변경 사항

| PR | 내용 |
|---|---|
| PR27 | `seed_demo`가 시연 계정의 게임 기록·차단·신고를 지우고 알림 설정을 기본값으로 되돌린다. 펜팔 친구·보관함 넘긴 편지·임시저장 장면 추가, 시연1 우표 9개 고정 |
| PR29 | 이 릴리스 설명서 |

- 마이그레이션 없음.

## 테스트

- PR27 브랜치에서 로컬 sqlite·PostgreSQL 17 `manage.py test` 172개 통과, `ruff`·`mypy`·`check`·`makemigrations --check` 통과.
- 배포 뒤 배포 서버에서 시연1 화면 기준 데이터를 확인한다.
- 원격 CI 없음.
