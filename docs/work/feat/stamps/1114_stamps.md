# 우표 · 수집 보상

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/stamps`
- 기준 커밋: `f3ec513`
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

우표 마스터를 20종으로 채우고, 우표첩 · 우표 상세 · 수집 보상 API를 만든다(STAMP-02~05). 편지 기능이 쓸 지급 함수와 보상 해금 판단도 여기서 만든다.

## 목표

- 우표에 `kind`(achievement/decoration), `grade`(common/rare/legendary)가 있고 20종이 시드된다.
- `GET /api/stamps/`, `GET /api/stamps/{code}/`, `GET /api/stamps/rewards/`, `POST /api/stamps/rewards/{code}/seen/`이 문서 레포 `api/stamps.md`대로 동작한다.
- 우표가 10개가 되면 「우표 수집가」를 자동으로 준다.
- 기존 `granted_stamps` 응답에 `kind`, `grade`가 더해진다(호환되는 추가).

## 범위

- 포함: Stamp 필드 추가 · 시드, 보상 확인 기록 모델, 우표 API 4개, 지급 · 해금 헬퍼, 테스트
- 제외: 편지 발송 때의 우표 지급 연결(편지 PR), 꾸미기 우표 지급 화면(운영자가 admin에서 지급)

## 참고한 상위 설계

- 문서 레포 `api/stamps.md`, `spec/stamp.md`, `screens/design-system.md` 6절, `screens/07_my-page.md` 7-4~7-8

## 작업 계획

1. Stamp 필드 추가 마이그레이션, 20종 시드
2. 보상 카탈로그와 해금 계산, 보상 확인 모델
3. 지급 헬퍼(`grant_stamps`, 수집가 자동 지급)
4. API 4개와 Swagger 설명
5. 테스트, 검사

## 세부 설계

- 수집 보상은 저장하지 않고 보유 우표 수로 계산한다. 열린 시각은 N번째로 받은 우표의 획득 시각이다. 모달 확인 여부만 `RewardSeen`에 저장한다.
- 우표 번호 No.05~12는 화면에서 확인하지 못해 목록 순서로 붙인다(가정, 문서 레포 `api/stamps.md`와 같음).
- 꾸미기 우표 등급은 일반으로 둔다(가정).
- `granted_with`(획득 계기 상대)는 `UserStamp.granted_with` 필드로 남긴다. 편지 PR에서 채운다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`, `python manage.py makemigrations --check --dry-run`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-14 | 작업 설계 작성 |

## 결정·변경 사항과 남은 일

- 편지 PR에서 첫 편지 · 첫 왕복 · 새벽 · 먼 길 · 손글씨 · 펜팔 · 꾸준한 편지 지급을 연결한다.
