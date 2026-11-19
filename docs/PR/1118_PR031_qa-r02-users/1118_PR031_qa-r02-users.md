# PR31 fix(users): 공백 닉네임은 INVALID_NICKNAME으로 (QA 2회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r02-users` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/31
- 관련 이슈: 해당 없음 (백엔드 QA 루프 2회차)
- 관련 설계: 문서 레포 `api/users.md` 「PATCH /api/users/me/」, `api/auth.md` 「POST /api/auth/signup/」
- 작업 설계: [docs/work/fix/qa-r02-users/1118_qa-r02-users.md](../../work/fix/qa-r02-users/1118_qa-r02-users.md)

## 목적

공백만 있는 닉네임의 에러 코드를 명세대로 `INVALID_NICKNAME`으로 맞춘다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 검증 | `apps/users/serializers.py` `SignupSerializer`, `NicknameUpdateSerializer` | `nickname`에 `allow_blank=True`. 공백만 있는 값도 `validate_nickname`으로 가서 400 `INVALID_NICKNAME` |
| 테스트 | `apps/users/tests.py` | 가입·닉네임 변경에서 공백 닉네임 2개 |

## 설계·결정 반영

- 명세(`api/users.md`, `api/auth.md`)의 400 `INVALID_NICKNAME`(길이 오류)에 공백만 있는 닉네임을 포함시켰다. 닉네임 확인 API는 이미 같은 동작이다.
- 범위 밖: 닉네임에 줄바꿈 같은 제어 문자를 허용할지는 명세에 없어 QA 진행 기록 「결정 필요」로 남겼다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 174개 통과(이 PR에서 2개 추가).
- 재현: 로컬 서버(8100, 수정 전 코드)에서 `PATCH /api/users/me/ {"nickname": "   "}` → 400 `VALIDATION_ERROR`("blank일 수 없습니다").
- PostgreSQL은 생략(모델·쿼리 변경 없음). 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `allow_blank=True`로 바뀌어도 `validate_nickname`이 길이 0을 거절하는지

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/users.md` 「PATCH /api/users/me/」, `api/auth.md` 「POST /api/auth/signup/」
