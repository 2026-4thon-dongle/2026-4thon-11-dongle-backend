# 프론트 연동 피드백 반영 (편지 API)

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/letter-api-feedback`
- 기준 커밋: `6ae298a`
- 상태: 완료
- 관련 PR: [PR16](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/16)

## 지금 작업 내용

프론트가 배포 서버에 연동하면서 올린 요청 2건과, 이전에 확인한 `is_read` 노출 문제를 고친다.

- 스티커 크기 `scale`을 저장하고 돌려준다 (문서 레포 `requests/1115_fe2be_sticker-scale.md`).
- 편지 응답의 시각을 한국 시간(`+09:00`)으로 통일한다 (`requests/1116_fe2be_letter-time-kst.md`).
- 편지 상세에서 보낸 사람에게 `is_read`가 내려가는 문제를 고친다.

## 목표

- `POST /api/letters/`에 `scale`을 보내면 저장되고, `GET /api/letters/{id}/`의 `stickers[]`에 `scale`이 나온다. 보내지 않거나 예전 편지면 0.18로 나온다.
- 범위(0.05~0.5) 밖의 `scale`은 `400 VALIDATION_ERROR`로 거절한다.
- API 응답의 모든 시각이 `+09:00`으로 나온다(편지·피드·우체통 포함).
- 보낸 편지의 `is_read`는 항상 `false`이고, 받은 편지에서만 실제 값이 나온다.

## 범위

- 포함: 스티커 검증·저장·응답, JSON 렌더러의 시간대 처리, `letter_detail` `is_read`, 테스트, 문서 레포 `api/letters.md`·`api/mailbox.md` 갱신(푸시는 사용자 확인 뒤), 요청 문서 응답
- 제외: 마이그레이션(스티커는 JSONField라 필요 없음), 편지 쓰기 외 API 변경
- 추가(진행 중 포함): 새벽 시간대에 실패하던 `test_first_letter`의 시각 고정

## 참고한 상위 설계

- 문서 레포 `api/letters.md` `POST /api/letters/`, `api/mailbox.md` 편지 상세, `api/common.md` 시간 규칙
- 백엔드 CLAUDE.md 10절 (`USE_TZ=True`, `Asia/Seoul`)

## 작업 계획

1. 스티커 `scale` 검증·저장·응답 + 테스트
2. JSON 렌더러가 aware datetime을 한국 시간으로 내리게 하고 테스트
3. `is_read` 수정 + 테스트
4. 검사 통과, PR 설명서
5. 문서 레포 api 문서·요청 응답 갱신

## 세부 설계

- **scale:** `validate_stickers`에서 `scale`을 읽는다. 없으면 0.18을 저장한다. 0.05 이상 0.5 이하가 아니면(`nan`, `inf` 포함) 형식 오류로 거절한다. 거절·보정 중 거절을 택한 이유는 `x`, `y` 범위 오류를 이미 거절하고 있어서 같은 규칙으로 맞추기 위해서다. 프론트 조절 범위(약 0.09~0.44)는 허용 범위 안이다. 상세 응답은 `scale`이 없는 예전 스티커에 0.18을 채워 내려 준다.
- **시각:** 원인은 `Response`에 `datetime`을 그대로 담는 곳(편지 보내기·예상·경로·상세·우체통 등)에서 DRF의 JSON 인코더가 UTC 값을 `Z`로 내리는 것이다. 시리얼라이저(`DateTimeField`)를 거치는 값은 이미 한국 시간이다. 곳곳의 뷰를 고치지 않고 `JSONRenderer`의 인코더가 aware datetime을 `timezone.localtime`으로 바꾸게 해, 앞으로 추가하는 API에서도 같게 나오도록 한다.
- **is_read:** `letter_detail`에서 받은 편지일 때만 `read_at`을 보고, 보낸 편지는 `false`로 둔다.

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`(sqlite로 로컬 실행), 시각은 응답 JSON 문자열이 `+09:00`으로 끝나는지 테스트로 확인

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-17 | 작업 설계 작성. 원격 `dev`가 없어 배포 브랜치 `chore/hosting-deploy`(`6ae298a`)에서 분기. 배포 서버가 그 브랜치를 따라가므로 이 브랜치를 거기에 병합하면 서버에 바로 반영된다(가정) |
| 2026-11-17 | Draft PR #16 생성(대상 `chore/hosting-deploy`). scale 검증·저장·응답, JSON 렌더러 한국 시간, `is_read` 수정과 테스트 구현. 로컬(sqlite) 137개 테스트 통과, 시각 테스트가 렌더러 없이는 실패함을 확인 |
| 2026-11-17 | 새벽에 실패하던 `test_first_letter`를 낮 시각 고정으로 수정 |

## 결정·변경 사항과 남은 일

- PR 대상은 `chore/hosting-deploy`로 하는 쌓기(stacked) 방식을 가정한다. `dev`가 생기면 대상을 바꾼다.
- `scale` 범위 밖은 거절로 정했다(요청 문서에서 거절·보정 중 선택을 요청함).
