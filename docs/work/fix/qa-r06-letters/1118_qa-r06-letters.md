# QA 6회차: 편지 스티커 입력 검증(500·잘못된 409)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r06-letters`
- 기준 커밋: `213bf20`
- 상태: 진행 중
- 관련 PR: [PR33](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/33)

## 지금 작업 내용

백엔드 QA 루프 6회차(편지 보내기)에서 찾은 문제를 고친다.

## 목표

- 스티커 `code`가 문자열이 아니면(리스트·객체 등) 500이 아니라 400 `VALIDATION_ERROR`가 나온다.
- 스티커 `rotation`(또는 `x`, `y`, `scale`)이 `"nan"`, `"inf"` 같은 유한하지 않은 수면 400 `VALIDATION_ERROR`가 나온다. 지금은 sqlite에서 409 `ALREADY_SENT`(저장 때 JSON 검사 실패를 중복 발송으로 잘못 읽음), PostgreSQL에서는 저장 오류로 500이 날 수 있다.

## 범위

- 포함: `LetterWriteSerializer.validate_stickers`, 테스트
- 제외: 스티커 회전 범위 제한(명세에 없음)

## 참고한 상위 설계

- 문서 레포 `api/letters.md` 「POST /api/letters/」: 스티커 형식·`scale` 범위 오류는 400 `VALIDATION_ERROR`

## 작업 계획

1. `code`가 `str`인지 먼저 본다.
2. `x`, `y`, `rotation`, `scale`이 `math.isfinite`인지 본다.
3. 테스트를 추가한다.

## 세부 설계

- 원인 1: `code not in STICKER_CODES`(set)에서 리스트·딕셔너리는 해시할 수 없어 `TypeError`가 난다. 지금 `try`는 `float()` 변환만 감싼다.
- 원인 2: `float("nan")`, `float("inf")`은 예외 없이 변환된다. `x`, `y`, `scale`은 범위 비교로 걸러지지만 `rotation`은 범위가 없어 그대로 저장된다. JSON에는 NaN이 없으므로 저장(`JSONField`)이나 응답 렌더링에서 실패한다.
- 고침: `isinstance(code, str)`이 아니거나 네 값 중 하나라도 `math.isfinite`가 아니면 「스티커 형식이 올바르지 않습니다.」로 거절한다.

## 확인 방법

- JSON 본문 `stickers: [{"code": ["x"], "x": 0.5, "y": 0.5}]` → 400 `VALIDATION_ERROR`
- `stickers: [{"code": "cat-wink", "x": 0.5, "y": 0.5, "rotation": "nan"}]` → 400 `VALIDATION_ERROR`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100)에서 재현: 리스트 code 500, 회전 `"nan"` 409 `ALREADY_SENT` |

## 결정·변경 사항과 남은 일

해당 없음
