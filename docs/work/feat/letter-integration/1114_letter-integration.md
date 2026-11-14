# 편지 알림과 기존 기능 연결

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/letter-integration`
- 기준 커밋: `a8f6d7b`
- 상태: 진행 중
- 관련 PR: PR12

## 지금 작업 내용

편지 앱이 생기면서 0이나 미지원으로 남겨 둔 기존 기능을 편지와 연결하고, 편지 알림을 만든다.

## 목표

- 편지가 출발하면 받는 사람에게 `letter_departed`, 도착하면 `letter_arrived` 알림이 생긴다.
- 대화의 첫 답장이 도착하면 받는 사람에게 `round_trip` 알림이 생긴다.
- 마이 페이지 `stats`의 `letter_count`, `penpal_count`와 일기의 `received_letter_count`가 실제 값을 준다.
- 받은 편지를 신고할 수 있다(`target_type=letter`).
- 탈퇴하면 편지와 손글씨 이미지도 지워진다.

## 범위

- 포함: 편지 알림 생성(출발·도착·왕복), 도착 알림 명령, 통계·받은 편지 수, 편지 신고, 탈퇴 정리
- 제외: 푸시 발송, `letter_location` 알림(배송 경로 PR 이후), `draft_count`(임시저장 PR에서 연결)

## 참고한 상위 설계

- 문서 레포 `api/notifications.md`(알림 종류별 이동 대상 표), `spec/settings.md`, `spec/safety.md`, `api/users.md`, `api/diaries.md`, `screens/03_home-feed.md` 3-4

## 작업 계획

1. `Letter.arrival_notified_at` 필드와 알림 생성 함수
2. 발송 때 출발 알림, 도착 알림 명령과 알림 조회 때 도착 처리
3. 마이 페이지 통계, 일기 받은 편지 수
4. 편지 신고, 탈퇴 정리
5. 테스트, 검사

## 세부 설계

- 도착 알림은 `notify_arrived_letters` 명령(1분마다 실행)으로 만든다. 스케줄러가 없어도 데모가 되도록 알림 목록·안 읽은 수를 조회할 때 그 사용자 몫도 먼저 처리한다. 한 편지에 한 번만 만든다(`arrival_notified_at`).
- 알림 문구는 화면 3-4를 따른다. 출발: 「OO님의 편지가 출발했어요」, 도착: 「OO님의 편지가 도착했어요」, 첫 왕복: 「첫 왕복 완료! OO님과 우표를 주고받았어요」.
- 편지 알림 토글 2개는 명세대로 푸시 발송에만 적용한다. 알림 센터에는 항상 남긴다.
- `letter_count`는 내가 보낸 편지와 도착한 받은 편지 수, `penpal_count`는 펜팔 친구 수다.
- `received_letter_count`는 그 일기에 도착한 첫 편지 수다(배송 중인 편지는 세지 않는다).
- 편지 신고는 내가 받고 도착한 편지만 할 수 있다. 신고 대상 사용자는 보낸 사람이다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`, `python manage.py makemigrations --check --dry-run`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-14 | 작업 설계 작성 |

## 결정·변경 사항과 남은 일

- `draft_count`는 임시저장 PR에서, `letter_location`은 배송 경로 PR 이후에 연결한다.
