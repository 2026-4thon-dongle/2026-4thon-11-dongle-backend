# PR17 직접 배달 게임 서버

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/delivery-game` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/17
- 관련 이슈: 없음 (문서 레포 HOLD-01, `requests/1110_be2fe_hold-entry-points.md`)
- 관련 설계: 문서 레포 `screens/09_hold.md` 9-1·9-2, `spec/stamp.md` STAMP-03, `api/game.md`, `spec/game.md`
- 작업 설계: [docs/work/feat/delivery-game/1117_delivery-game.md](../../work/feat/delivery-game/1117_delivery-game.md)

## 목적

보류였던 직접 배달 게임을 사용자 결정으로 범위에 넣는다. 배송 중인 편지로 30초 미니 게임을 하면 서버가 결과를 검증해 도착 시간을 줄이고, 기존 꾸미기 우표 8종을 조건에 따라 준다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 앱 | `apps/games/` (`apps.py`, `admin.py`), `config/settings/base.py` | 새 앱 등록, admin에서 판 기록 조회 |
| 모델 | `apps/games/models.py`, `migrations/0001_initial.py` | `GameRun`(판 한 번: 편지, 구간, 시드, 코스, 상태, 시각, 결과, 단축 시간, 받은 우표) |
| 규칙 | `apps/games/rules.py` | 판 길이, 별 기준, 단축량, 상한 50%, 판수 제한, 데모 모드 환산, 우표 조건 8개 |
| 코스 | `apps/games/course.py` | 시드로 같은 코스. 한 줄에 조각·물웅덩이 각각 하나 이하 |
| 서비스 | `apps/games/services.py` | 편지 상태 계산, 시작(제한·이전 판 무효), 종료(검증, 편지 잠금 후 `arrives_at` 단축, 우표 지급) |
| API | `apps/games/views.py`, `serializers.py`, `urls.py`, `config/urls.py` | `GET /api/game/`, `GET /api/game/letters/{id}/`, `POST /api/game/runs/`, `POST /api/game/runs/{id}/finish/` |
| 테스트 | `apps/games/tests.py` | 18개: 코스 결정성·풀 수 있음, 별, 홈·접근 권한, 연습, 단축·상한·바닥, 편지·하루 제한, 결과 검증, 만료·무효, 우표 조건, 먼 길, 수집 보상, 데모 모드 |

## 설계·결정 반영

- 규칙과 보상은 작업 설계의 「세부 설계」를 따른다. 수치는 `rules.py` 한 곳에 있다.
- 새 우표·보상·알림 종류를 만들지 않는다. 기존 데이터에서 바뀌는 것은 `Letter.arrives_at`과 `UserStamp`뿐이다. 도착 알림은 기존 `notify_arrived_letters`가 줄어든 `arrives_at`을 그대로 따른다.
- 꾸미기 우표의 설명 문구(「시즌 이벤트에서 받았어요」)는 기존 데이터라 바꾸지 않고, 게임 조건 문구는 게임 API의 `goals[].condition`으로 준다.
- 결과 검증은 서버 시각(시작 25초 뒤 ~ 3분)과 코스의 최대값으로만 한다. 입력 기록을 재생하는 검증은 하지 않는다(해커톤 범위, 가정).
- 가정: 처음에는 원격 `dev`가 없어 `chore/hosting-deploy`에서 분기했다. PR18로 `dev`가 다시 생기면서 GitHub가 대상을 `dev`로 바꿨고, 최신 `dev`를 이 브랜치에 병합(merge commit)했다.

## 디자인 영향

해당 없음 (화면은 frontend PR #96)

## 테스트

- 로컬(sqlite): `ruff format --check`, `ruff check`, `mypy .`, `manage.py check`, `makemigrations --check`, `manage.py test` 155개 통과(게임 18개 포함), `spectacular` 경고 없음.
- 로컬 연동: 이 브랜치를 `runserver`로 띄우고 frontend PR #96 화면에서 실제로 플레이했다. 시작 → 30초 → 결과(별 0개, 단축 없음)와 성공(별 1개 → 도착 10분 단축, 「별사탕」 지급)을 확인했다.
- PostgreSQL로는 돌리지 않았다(새 쿼리는 집계·`select_for_update`뿐이고 sqlite에서는 잠금이 무시된다. 배포 서버는 PostgreSQL이므로 배포 뒤 한 판 확인이 필요하다).
- 테스트 데이터·계정 변경 없음(로컬 확인용 계정은 임시 sqlite에만 만들었다).

## 리뷰어가 볼 곳

- `services.py` `finish_run`: 만료 처리 저장 뒤 트랜잭션 밖에서 에러를 내는 부분, 편지 잠금 후 상한·바닥 계산.
- `course.py`: 모든 조각을 줍는 길이 있다는 보장(무지개 편지 우표 조건과 연결).

## 배포·마이그레이션 메모

새 테이블(`games_gamerun`)만 만드는 마이그레이션이 있다. 배포 때 `migrate`가 자동으로 돈다. 프론트(PR #96)는 이 PR이 배포된 뒤에 병합해야 한다.

## 관련 문서

- 문서 레포 `api/game.md`, `spec/game.md`, `changes/1117_be_delivery-game.md` (로컬 커밋, 푸시 전)
- frontend PR #96
