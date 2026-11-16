# 직접 배달 게임 (HOLD-01)

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/delivery-game`
- 기준 커밋: `6ae298a`
- 상태: 진행 중
- 관련 PR: [PR17](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/17)

## 지금 작업 내용

보류였던 「직접 배달 게임」(Figma 9-1, 9-2)을 사용자 지시로 범위에 넣어 서버 쪽을 만든다. 배송 중인 편지를 고향이가 직접 배달하는 30초 미니 게임이다. 잘하면 편지 도착 시간이 줄고, 기존 꾸미기 우표 8종을 받는다. 프론트 화면은 프론트 레포에서 따로 만든다.

## 목표

- 배송 중인 편지(보낸 편지와 나에게 오는 편지)로 게임을 시작하면 서버가 코스를 만들어 준다. 편지 없이 연습할 수도 있다.
- 결과를 보내면 서버가 검증해 별(0~3)을 매기고, 편지의 `arrives_at`을 줄이고, 조건을 채운 꾸미기 우표를 준다.
- 새 우표·새 보상·새 알림 종류를 만들지 않는다. 기존 시스템에서 바뀌는 데이터는 `Letter.arrives_at`과 `UserStamp`뿐이다.

## 범위

- 포함: `apps/games` 앱(모델, 코스 생성, 규칙, API 4개), 마이그레이션(새 테이블만), 테스트, admin
- 제외: 프론트 화면(프론트 레포), 알림, 새 우표·보상, 랭킹, 실시간 조작 검증(입력 기록 재생)

## 참고한 상위 설계

- 문서 레포 `screens/09_hold.md` 9-1·9-2, `spec/features.md` HOLD-01, `spec/stamp.md` STAMP-03(꾸미기 우표 획득처: 배달 게임·시즌 이벤트)
- 문서 레포 `requests/1110_be2fe_hold-entry-points.md`: 백엔드가 숨김을 제안했던 요청. 이번 작업으로 방향이 바뀐다(사용자 결정, 2026-11-17).
- 백엔드 우표 지급 `apps.stamps.services.grant_stamps`, 수집 보상 `rewards_unlocked_between`

## 작업 계획

1. 앱 뼈대와 모델 `GameRun`, 마이그레이션
2. 규칙 상수와 코스 생성(시드로 같은 코스), 별 계산
3. 시작·종료 서비스(제한, 단축, 우표 지급)
4. API 4개와 Swagger 문서
5. 테스트
6. 문서 레포 `api/game.md`·`spec/game.md` 초안(푸시는 사용자 확인 뒤)

## 세부 설계

### 규칙

| 항목 | 값 |
|---|---|
| 한 판 | 30초, 3개 레인. 코스는 서버가 시드로 만든다 |
| 요소 | 우표 조각(줍기), 물웅덩이(피하기) |
| 별 3개 | 조각 85% 이상, 부딪힘 1회 이하 |
| 별 2개 | 조각 65% 이상, 부딪힘 2회 이하 |
| 별 1개 | 조각 40% 이상 |
| 단축 | 별 수 × 10분. 데모 모드(`LETTER_DEMO_MODE`)에서는 별 수 × 10초 |
| 편지 상한 | 한 편지에 줄일 수 있는 총시간은 배송 시간의 50%(보낸 사람·받는 사람 합산) |
| 남은 시간 | 시작하려면 도착까지 10분(데모 10초) 이상 남아야 한다. 줄인 뒤에도 1분(데모 1초)은 남긴다 |
| 편지당 판수 | 한 사람이 한 편지로 3판까지 |
| 하루 판수 | 한 사람이 하루(한국 시간) 10판까지. 연습 포함 |
| 판 유효 시간 | 시작 뒤 3분. 새 판을 시작하면 끝내지 않은 이전 판은 무효 |
| 결과 검증 | 시작부터 25초가 지나야 받는다. 조각·부딪힘 수는 코스에 있는 수를 넘을 수 없다 |

- 시간 값은 API에서 모두 초 단위로 준다(`reduced_seconds` 등). 데모 모드에서도 같은 필드를 쓴다.
- 연습(편지 없음)은 단축이 없고, 「먼 길」 우표를 뺀 우표 조건에는 포함된다. 데모 모드에서 편지가 1분 만에 도착하므로 시연은 연습으로도 할 수 있다.

### 보상: 기존 꾸미기 우표 8종

| 우표 | 조건 |
|---|---|
| `star-candy` 별사탕 | 첫 배달 성공(별 1개 이상) |
| `strawberry-cat` 딸기 고양이 | 처음으로 별 3개 |
| `cloud-bread` 구름빵 | 성공 5회 |
| `tulip` 튤립 | 별 3개 3회 |
| `little-whale` 꼬마 고래 | 12시간 구간(`far`) 편지를 별 3개로 배달 |
| `rainbow-letter` 무지개 편지 | 한 판에서 조각을 모두 줍고 부딪힘 0회 |
| `tangerine` 제철 귤 | 성공 10회 |
| `bungeoppang` 붕어빵 | 성공 15회 |

- 지급은 `grant_stamps`로 한다. 우표 10개째에 「우표 수집가」가 같이 나가고, 수집 보상(스티커·편지지·글씨체)은 기존처럼 보유 우표 수로 열린다.
- 꾸미기 우표의 설명 문구(「시즌 이벤트에서 받았어요」)는 기존 데이터라 바꾸지 않는다. 게임 조건 문구는 게임 API가 따로 준다.

### 모델

`GameRun`: `user`, `letter`(null이면 연습, 편지 삭제 시 null), `band`(시작 때 편지 구간), `seed`, `course`(JSON), `piece_total`, `puddle_total`, `status`(`playing`/`finished`/`expired`/`abandoned`), `started_at`, `expires_at`, `finished_at`, `pieces`, `hits`, `stars`, `reduced_seconds`, `granted_stamps`(코드 목록).

### API (`/api/game/`)

| 메서드·경로 | 내용 |
|---|---|
| `GET /api/game/` | 규칙, 오늘 남은 판수, 내 기록, 우표 목표 8개(보유·진행), 게임할 수 있는 배송 중 편지 목록 |
| `GET /api/game/letters/{id}/` | 편지 하나의 게임 상태(가능 여부와 이유, 남은 시간, 남은 판수, 줄일 수 있는 시간) |
| `POST /api/game/runs/` | 판 시작. `letter_id`가 없으면 연습. 코스를 준다 |
| `POST /api/game/runs/{id}/finish/` | 결과(`pieces`, `hits`) 제출. 별, 단축, 새 도착 시각, 받은 우표, 열린 수집 보상 |

에러 코드: `NOT_FOUND`(내 편지·판이 아님, 차단), `LETTER_ARRIVED`, `ARRIVING_SOON`, `PLAY_LIMIT`, `REDUCE_LIMIT`, `DAILY_LIMIT`(429), `RUN_TOO_FAST`, `RUN_EXPIRED`, `RUN_FINISHED`, `VALIDATION_ERROR`.

### 동시성

같은 편지로 두 사람이 동시에 끝내도 상한을 넘지 않게 종료 처리에서 편지 행을 `select_for_update`로 잠그고, 그 편지로 이미 줄인 시간을 합산해 계산한다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `makemigrations --check`, `python manage.py test`(로컬 sqlite), Swagger 스키마 경고 확인

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-17 | 작업 설계 작성. 원격 `dev`가 없어 배포 브랜치 `chore/hosting-deploy`(`6ae298a`)에서 분기하고 PR도 그 브랜치로 둔다(PR16과 같은 쌓기 방식, 가정) |

## 결정·변경 사항과 남은 일

- 게임을 범위에 넣은 것은 사용자 결정이다(2026-11-17). 팀(기획·프론트) 공지와 문서 레포 `1110_be2fe_hold-entry-points` 정리가 필요하다.
- 규칙 수치(별 기준, 단축량, 상한)는 시연 뒤 조정할 수 있게 `apps/games/rules.py` 한 곳에 둔다.
