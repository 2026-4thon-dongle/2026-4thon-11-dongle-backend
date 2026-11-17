# QA 12회차: 주간 글감 알림에 글감 id 넣기

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r12-notifications`
- 기준 커밋: `213bf20`
- 상태: 리뷰 중
- 관련 PR: [PR34](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/34)

## 지금 작업 내용

백엔드 QA 루프 12회차(알림)에서 찾은 문제를 고친다.

## 목표

- `create_weekly_prompt_notifications`가 만드는 `prompt` 알림의 `target_id`가 그 주 글감 id다. 지금은 null이라 프론트가 알림을 눌러 6-1 일기 쓰기로 보낼 때 글감을 알 수 없다.

## 범위

- 포함: 주간 글감 알림 명령, 테스트
- 제외: 이미 만들어진 알림(배포 서버 데이터)은 고치지 않는다

## 참고한 상위 설계

- 문서 레포 `api/notifications.md` 개요 표: `prompt` → `target_id` 글감 id → 6-1 일기 쓰기
- `spec/diary.md` 미정 사항: 「주간 글감 알림의 `target_id`가 글감 id를 가리킨다」

## 작업 계획

1. `Notification(...)`에 `target_id=prompt.id`를 넣는다.
2. 테스트를 추가한다.

## 세부 설계

- 그 주 글감(`prompts[week % len]`)의 id를 그대로 넣는다. 제목·본문은 바꾸지 않는다.

## 확인 방법

- 명령을 실행한 뒤 `GET /api/notifications/`의 `prompt` 알림 `target_id`가 활성 글감 id 중 하나이고 `body`가 그 글감 문구와 같다.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100, PostgreSQL)에서 재현: `prompt` 알림 `target_id` null |
| 2026-11-18 | 글감 알림 target_id와 테스트 1개. sqlite 173개 통과 |

## 결정·변경 사항과 남은 일

- 배포 서버에 이미 만들어진 글감 알림은 `target_id`가 null로 남는다. 다음 주 월요일부터 새 알림에 들어간다.
