# PR33 fix(letters): 스티커 code·숫자 검증으로 500과 잘못된 409 막기 (QA 6회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r06-letters` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/33
- 관련 이슈: 해당 없음 (백엔드 QA 루프 6회차)
- 관련 설계: 문서 레포 `api/letters.md` 「POST /api/letters/」
- 작업 설계: [docs/work/fix/qa-r06-letters/1118_qa-r06-letters.md](../../work/fix/qa-r06-letters/1118_qa-r06-letters.md)

## 목적

편지 스티커의 `code` 타입과 숫자 값(유한한 수)을 검증해 400 `VALIDATION_ERROR`로 거절한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 검증 | `apps/letters/serializers.py` `validate_stickers` | `code`가 `str`이 아니거나 `x`·`y`·`rotation`·`scale` 중 하나라도 유한한 수가 아니면 400 `VALIDATION_ERROR` |
| 테스트 | `apps/letters/tests.py` | `test_sticker_bad_code_or_number_is_validation_error` (리스트·객체·숫자 code, rotation nan·inf·-Infinity) |

## 설계·결정 반영

- 명세의 「스티커 형식 오류는 400 `VALIDATION_ERROR`」를 따른다. 에러 문구는 기존 「스티커 형식이 올바르지 않습니다.」를 쓴다.
- 회전 범위(예: -180~180)는 명세에 없어 제한하지 않았다. 유한한 수인지만 본다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 173개 통과(이 PR에서 1개 추가).
- 재현(수정 전, 로컬 서버 8100): `stickers=[{"code": ["x"], ...}]` → 500 HTML(`TypeError: unhashable type`), 시연1이 `rotation: "nan"`으로 보내면 409 `ALREADY_SENT`(sqlite JSON 검사 실패가 `IntegrityError`로 잡힘).
- PostgreSQL은 생략(검증 코드만 바뀌고 모델·쿼리 변경 없음). 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `validate_stickers`의 검사 순서: 타입·유한성 → code 목록·x·y 범위 → scale 범위

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/letters.md` 「POST /api/letters/」
