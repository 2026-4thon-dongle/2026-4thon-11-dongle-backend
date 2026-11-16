# PR19 feat: 시연용 데이터 생성 명령 seed_demo

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/demo-seed` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/19
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/` (데이터가 보이는 API), `spec/letter.md` 배송 구간
- 작업 설계: [docs/work/feat/demo-seed/1117_demo-seed.md](../../work/feat/demo-seed/1117_demo-seed.md)

## 목적

시연 때 피드·우체통·배송 중·우표첩이 비어 있지 않도록 시연용 계정과 데이터를 한 번에 만드는 관리 명령을 추가한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 기능 | `apps/users/demo_seed.py` | 시연 계정 5개·일기 10개·편지 7통·우표를 만든다. 다시 실행하면 시연 계정끼리의 데이터만 지우고 다시 만든다. `remove()`는 시연 계정을 지운다 |
| 명령 | `apps/users/management/commands/seed_demo.py` | `seed_demo [--arrive-in N] [--remove]` |
| 테스트 | `apps/users/tests_demo_seed.py` | 시나리오(우체통·배송 중·우표·피드), 데모 모드에서도 배송 중 유지, 멱등성(계정 id·건수 동일), 다른 사용자 데이터 보존, 섞인 대화 보존, 닉네임 충돌 시 무변경 |
| 배포 | `compose.yaml`, `.env.example` | 한 번짜리 서비스 `demo-seed`. `DEMO_SEED=true`일 때만 `seed_demo --arrive-in ${DEMO_ARRIVE_IN:-3}` 실행 |
| 문서 | `README.md` 「시연 준비」, `docs/report/1117_9756231_test-data.md` | 시연 데이터 사용법, 데모 모드 켜고 끄기, 시연 확인 순서, 계정·데이터 목록 |
| 문서 | `docs/work/` | 병합된 홈서버 배포·편지 피드백 작업 설계 상태를 완료로 바꿈 |

## 설계·결정 반영

작업 설계 「세부 설계」를 따른다. 가정한 내용은 다음과 같다.

- 시연 계정 도메인 `@dongle-demo.ac.kr`, 닉네임·일기·편지 문구는 임의로 정했다.
- 데이터는 `send_letter`·`grant_stamps` 서비스 함수로 만들어 구간·우표·출발 알림 규칙을 API와 같게 따르고, 시각만 옮긴다. 배송 중 편지는 데모 모드와 관계없이 실제 구간 시간을 쓴다.
- 배포 서버에 셸 실행 도구가 없어 compose 한 번짜리 서비스와 환경변수로 실행한다.
- 다른 사용자의 대화나 임시저장이 달린 시연 일기는 지우지 않는다. 그런 일기가 남으면 다시 실행할 때 시연 계정의 일기가 그만큼 늘어난다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 143개 통과(이 PR에서 6개 추가).
- 로컬 PostgreSQL 17(docker): `manage.py test` 143개 통과.
- 로컬 docker compose(`DEBUG=False`, `LETTER_DEMO_MODE=True`, `DEMO_SEED=true`): `demo-seed`가 「시연 계정 5개, 일기 10개, 편지 7통」을 만들고, 컨테이너를 다시 시작해도 계정 id(1~5)와 건수가 같았다. 시연1로 피드(시연2 일기 2개), 새 편지 1통, 대화 2개, 배송 중 3통, 우표 8개(스티커·「밤하늘」 보상 열림), 알림 3개를 확인했다.
- 배포 서버 실행은 병합 후 `DEMO_SEED`를 넣을 때 한다(이 PR에서는 하지 않음).
- 원격 CI 없음. 테스트 데이터 문서 `docs/report/1117_9756231_test-data.md`를 새로 만들었다.

## 리뷰어가 볼 곳

- `demo_seed._clear`: 지우는 범위가 시연 계정끼리의 데이터로만 제한되는지
- `demo_seed._in_transit`, `_deliver`: 시각을 옮기는 방식

## 배포·마이그레이션 메모

- 새 마이그레이션 없음. 병합하면 배포 서버에 `demo-seed` 컨테이너가 생기지만 `DEMO_SEED`가 없으면 메시지만 남기고 끝난다.
- 시연 데이터를 넣으려면 플랫폼 환경변수 `DEMO_SEED=true`를 넣고 다시 배포한다(사용자 확인 후).

## 관련 문서

- 문서 레포 `api/feed.md`, `api/mailbox.md`, `api/letters.md`, `api/stamps.md`
