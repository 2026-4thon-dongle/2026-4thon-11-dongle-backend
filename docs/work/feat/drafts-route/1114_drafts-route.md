# 편지 임시저장과 배송 경로

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/drafts-route`
- 기준 커밋: `d16d43e`
- 상태: 완료
- 관련 PR: PR13

## 지금 작업 내용

편지 임시저장 API 4개(LETTER-11)와 실시간 배송 지도용 경로 API(LETTER-10)를 만든다. 임시저장을 편지 발송, 피드 일기 상세, 마이 페이지 통계와 연결한다.

## 목표

- 문서 레포 `api/letters.md`의 `GET/POST /api/letters/drafts/`, `GET/DELETE /api/letters/drafts/{id}/`, `GET /api/letters/{id}/route/`가 명세대로 동작한다.
- 발송하면 이어 쓴 임시저장이 지워진다. 피드 일기 상세 `my_draft`, 마이 페이지 `draft_count`가 실제 값을 준다.

## 범위

- 포함: `Draft` 모델, 임시저장 API 4개, 배송 경로 API, 발송·피드·통계 연결, 테스트
- 제외: `letter_location` 배송 위치 알림(경로 계산만 하고 알림은 만들지 않는다)

## 참고한 상위 설계

- 문서 레포 `api/letters.md`, `spec/letter.md`, `screens/04_letter-write.md`(4-8, 4-9, 4-12), `screens/07_my-page.md`(7-3)

## 작업 계획

1. `Draft` 모델과 임시저장 API 4개
2. 발송·피드 일기 상세·통계 연결
3. 배송 경로 계산과 API
4. 테스트, 검사

## 세부 설계

- 임시저장은 사용자마다 대상(일기 또는 받은 편지)당 1통이다. 같은 대상에 다시 저장하면 덮어쓰고 200을 준다. 서명·스티커·우표는 저장하지 않는다(명세 가정).
- 발송하면 `draft_id`의 임시저장과 같은 대상의 임시저장을 지운다.
- 경유지는 출발·도착 시·도 대표 좌표를 잇는 직선 위의 점마다 가장 가까운 시·도를 골라 지나는 순서대로 둔다(출발·도착 시·도는 뺀다). 경유지 지역은 시·도 단위다(가정, 시·군 좌표가 없다).
- 경유지 `story`는 그 시·도에서 쓴 일기 중 조회자가 볼 수 있는 최신 일기 한 줄이다.
- `map_theme`은 편지 id로 정해 편지마다 고정한다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`, `python manage.py makemigrations --check --dry-run`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-14 | 작업 설계 작성 |
| 2026-11-14 | `Draft` 모델, 임시저장 API 4개, 배송 경로 API, 발송·피드·통계 연결 구현. 테스트 9개 추가, 전체 133개 통과. 아직 도착하지 않은 편지에는 답장 임시저장을 만들 수 없게 했다(404). 저장소 CLAUDE.md 현재 단계 갱신 |

## 결정·변경 사항과 남은 일

- 해당 없음
