# QA 2회차: 공백 닉네임의 에러 코드를 INVALID_NICKNAME으로

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r02-users`
- 기준 커밋: `213bf20`
- 상태: 진행 중
- 관련 PR: [PR31](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/31)

## 지금 작업 내용

백엔드 QA 루프 2회차(내 정보·설정·지역 수정·탈퇴)에서 찾은 문제를 고친다.

## 목표

- 공백만 있는 닉네임으로 닉네임 변경(`PATCH /api/users/me/`)이나 가입(`POST /api/auth/signup/`)을 하면 400 `INVALID_NICKNAME`이 나온다. 지금은 400 `VALIDATION_ERROR`("blank일 수 없습니다")가 나온다.

## 범위

- 포함: 닉네임 변경·가입 serializer의 `nickname` 필드, 테스트
- 제외: 닉네임에 쓸 수 있는 문자 규칙(줄바꿈 등) — 명세에 없어 QA 진행 기록 「결정 필요」로 남긴다

## 참고한 상위 설계

- 문서 레포 `api/users.md` 「PATCH /api/users/me/」 400 `INVALID_NICKNAME`(길이 오류), `api/auth.md` 「POST /api/auth/signup/」 400 `INVALID_NICKNAME`
- 닉네임 확인 API(`GET /api/auth/nickname/check/`)는 이미 공백 닉네임을 `INVALID_NICKNAME`으로 돌려준다

## 작업 계획

1. `NicknameUpdateSerializer`, `SignupSerializer`의 `nickname`에 `allow_blank=True`를 주어 빈 값도 `validate_nickname`(앞뒤 공백 제거 뒤 길이 검사)으로 보낸다.
2. 테스트를 추가한다.

## 세부 설계

- DRF `CharField`는 앞뒤 공백을 지운 뒤 빈 문자열이면 `validate_*` 전에 `blank` 에러를 낸다. `allow_blank=True`면 빈 문자열이 `validate_nickname`으로 가서 길이 0 → `INVALID_NICKNAME`이 된다.
- `NicknameUpdateSerializer`는 `validate_nickname`을 뷰에서 부르므로 필드 옵션만 바꾸면 된다. `SignupSerializer`는 `validate_nickname` 메서드가 있다.

## 확인 방법

- `PATCH /api/users/me/ {"nickname": "   "}` → 400 `INVALID_NICKNAME`
- `POST /api/auth/signup/`에 `nickname: "  "` → 400 `INVALID_NICKNAME`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100)에서 재현 |

## 결정·변경 사항과 남은 일

- 닉네임에 줄바꿈·제어 문자를 허용할지는 명세에 없다(QA 진행 기록 「결정 필요」).
