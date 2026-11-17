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

(작업 중)

## 설계·결정 반영

작업 설계 「세부 설계」를 따른다.

## 디자인 영향

해당 없음

## 테스트

(작업 중)

## 리뷰어가 볼 곳

(작업 중)

## 배포·마이그레이션 메모

마이그레이션 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다. 배포 때 `DEMO_SEED=true`면 `demo-seed`가 새 시드를 돈다.

## 관련 문서

- 문서 레포 시연 안내(이 PR 뒤에 작성)
