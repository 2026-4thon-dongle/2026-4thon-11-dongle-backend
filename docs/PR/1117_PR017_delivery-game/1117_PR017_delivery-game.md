# PR17 직접 배달 게임 서버

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/delivery-game` → `chore/hosting-deploy`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/17
- 관련 이슈: 없음 (문서 레포 HOLD-01, `requests/1110_be2fe_hold-entry-points.md`)
- 관련 설계: 문서 레포 `screens/09_hold.md` 9-1·9-2, `spec/stamp.md` STAMP-03
- 작업 설계: [docs/work/feat/delivery-game/1117_delivery-game.md](../../work/feat/delivery-game/1117_delivery-game.md)

## 목적

보류였던 직접 배달 게임을 사용자 결정으로 범위에 넣는다. 배송 중인 편지로 30초 미니 게임을 하면 서버가 결과를 검증해 도착 시간을 줄이고, 기존 꾸미기 우표 8종을 조건에 따라 준다.

## 변경 사항

(작업이 끝나면 채운다)

## 설계·결정 반영

- 규칙과 보상은 작업 설계의 「세부 설계」를 따른다.
- 새 우표·보상·알림 종류를 만들지 않는다. 기존 데이터에서 바뀌는 것은 `Letter.arrives_at`과 `UserStamp`뿐이다.
- 가정: 원격 `dev`가 없어 배포 브랜치 `chore/hosting-deploy`에서 분기하고 PR 대상도 그 브랜치로 둔다.

## 디자인 영향

해당 없음 (화면은 프론트 레포)

## 테스트

(작업이 끝나면 채운다)

## 리뷰어가 볼 곳

(작업이 끝나면 채운다)

## 배포·마이그레이션 메모

새 테이블(`games_gamerun`)만 만드는 마이그레이션이 있다. 배포 때 `migrate`가 자동으로 돈다.

## 관련 문서

- 문서 레포 `api/game.md`, `spec/game.md` (이 PR과 함께 초안 작성)
