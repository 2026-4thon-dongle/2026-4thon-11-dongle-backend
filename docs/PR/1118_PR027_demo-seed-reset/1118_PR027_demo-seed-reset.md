# PR27 시연 데이터 처음부터 다시 만들기

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/demo-seed-reset` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/27
- 관련 이슈: 없음
- 관련 설계: `docs/report/1117_9756231_test-data.md`, 문서 레포 `api/mailbox.md`(펜팔·보관함·임시저장)
- 작업 설계: [docs/work/feat/demo-seed-reset/1118_demo-seed-reset.md](../../work/feat/demo-seed-reset/1118_demo-seed-reset.md)

## 목적

사용자 지시(「시연 데이터 처음부터 다시 다 만들어줘」)로 `seed_demo`가 시연 계정을 처음 상태로 되돌리게 하고, 시연할 수 있는 장면을 늘린다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 초기화 | `apps/users/demo_seed.py` `_clear`, `_ensure_user` | 시연 계정의 게임 기록(`GameRun`), 시연 계정이 건 차단·신고를 지우고 알림 설정을 기본값으로 되돌린다. 다른 사용자가 시연 계정을 차단·신고한 기록은 남긴다 |
| 장면 | `apps/users/demo_seed.py` `_create` | 펜팔 친구(시연1 ↔ 시연5 편지 6통, 왕복 3번, 시연1의 「내 차례」), 보관함의 넘긴 편지(시연4 → 시연1), 임시저장(시연1 → 시연3 일기) |
| 우표 | `apps/users/demo_seed.py` | 시연1에게 「새벽 편지」를 늘 줘서 실행 시각과 관계없이 우표 9개. 배달 게임 첫 성공으로 10개째 「우표 수집가」 보상이 열린다 |
| 테스트 | `apps/users/tests_demo_seed.py` | 편지 수 14통, 펜팔·보관·임시저장·우표 9개, 초기화 범위(게임·차단·신고·설정, 다른 사용자 차단은 남김) |
| 문서 | `docs/report/1117_9756231_test-data.md` | 초기화 범위, 편지 14통 표, 테스트할 수 있는 기능 갱신 |

## 설계·결정 반영

작업 설계 「세부 설계」를 따른다.

## 디자인 영향

해당 없음

## 테스트

- 로컬 sqlite: `ruff format --check`, `ruff check`, `mypy .`, `manage.py check`, `makemigrations --check`, `manage.py test` 172개 통과(시드 테스트 8개).
- 로컬 PostgreSQL 17(docker 임시 컨테이너): `manage.py test` 172개 통과.
- 임시 sqlite에 `seed_demo`를 돌려 시연1이 보는 값을 확인했다. 우체통 요약은 새 편지 1·내 차례 1·배송 중 3, 보관함은 넘긴 편지 1, 펜팔은 강릉커피, 임시저장 1, 우표 9/20(다음 보상까지 1개).
- 배포 서버 확인은 릴리스 뒤에 한다.

## 리뷰어가 볼 곳

- `_clear`: 차단·신고는 시연 계정이 건 것만 지운다(`blocker`·`reporter` 기준).
- 펜팔 편지 6통은 `send_letter`로 만들고 보낸 시각을 과거로 옮긴다. 시연5 일기(3일 4시간 전) 뒤에 시작한다.

## 배포·마이그레이션 메모

마이그레이션 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다. 배포 때 `DEMO_SEED=true`면 `demo-seed`가 새 시드를 돈다.

## 관련 문서

- 문서 레포 시연 안내(이 PR 뒤에 작성)
