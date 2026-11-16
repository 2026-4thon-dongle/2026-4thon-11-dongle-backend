# PR16 스티커 scale 저장, 시각 한국 시간 통일, is_read 노출 수정

- 작성일: 2026-11-17
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/letter-api-feedback` → `chore/hosting-deploy`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/16
- 관련 이슈: 없음 (문서 레포 요청 `1115_fe2be_sticker-scale`, `1116_fe2be_letter-time-kst`)
- 관련 설계: 문서 레포 `api/letters.md` `POST /api/letters/`, `api/mailbox.md` 편지 상세, `api/common.md` 시간 규칙
- 작업 설계: [docs/work/fix/letter-api-feedback/1117_letter-api-feedback.md](../../work/fix/letter-api-feedback/1117_letter-api-feedback.md)

## 목적

프론트가 배포 서버에 연동하며 찾은 문제를 고친다.

- 스티커 크기(`scale`)를 서버가 받기만 하고 버려서, 받는 사람 화면이 보낸 사람이 만든 모양과 달랐다.
- 일부 API(편지 보내기·예상·경로·상세, 우체통 등)의 시각이 명세와 달리 UTC(`Z`)로 나왔다.
- 편지 상세에서 보낸 사람에게도 받는 사람의 읽음 여부(`is_read`)가 내려갔다. 읽음 표시를 쓰지 않는다는 원칙과 명세(받은 편지일 때만)에 어긋난다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 기능 | `apps/letters/serializers.py` | 스티커 `scale` 검증(0.05~0.5, 생략하면 0.18)·저장. 범위 밖·숫자가 아닌 값은 `400 VALIDATION_ERROR` |
| 기능 | `apps/letters/mailbox_views.py` | 편지 상세 `stickers[]`에 `scale`을 내려 줌. 저장돼 있지 않은 예전 편지는 0.18 |
| 문서화 | `apps/letters/mailbox_serializers.py` | 상세 `stickers` 설명에 `scale` 추가 |
| 수정 | `config/renderers.py`, `config/settings/base.py` | JSON 렌더러가 aware datetime을 `Asia/Seoul`로 바꿔 내림. 뷰가 `datetime`을 그대로 담는 API 전체에 적용 |
| 수정 | `apps/letters/mailbox_views.py` | `is_read`를 받은 편지에서만 실제 값으로, 보낸 편지는 `false` |
| 테스트 | `apps/letters/tests.py`, `tests_mailbox.py` | scale 저장·기본값·예전 편지·범위, 시각 `+09:00`, 보낸 편지 `is_read` 추가. `test_first_letter`는 낮 시각으로 고정 |

## 설계·결정 반영

- `scale` 범위 밖은 거절로 정했다. 요청 문서가 거절·보정 중 선택을 맡겼고, 같은 스티커의 `x`, `y` 범위 오류를 이미 거절하고 있어 맞췄다. 허용 범위 0.05~0.5는 요청 문서가 제안한 값이고, 프론트 조절 범위(약 0.09~0.44)를 포함한다. 요청의 「0 초과 1 이하」 표현과는 다르므로 `api/letters.md`에 허용 범위를 명시한다.
- 시각은 뷰마다 고치지 않고 렌더러에서 한 번에 맞췄다. 시리얼라이저를 거치는 값은 원래 한국 시간이라 달라지지 않는다. 같은 순간이라 프론트가 `Date`로 해석하는 데는 영향이 없다.
- 가정: 원격 `dev`가 없어 이 브랜치를 배포 브랜치 `chore/hosting-deploy`에서 분기하고 PR 대상도 그 브랜치로 둔 쌓기 PR이다. 배포 서버가 그 브랜치를 따라가므로 병합하면 자동 배포된다. `dev`가 다시 생기면 대상을 바꾼다.
- 마이그레이션은 없다(스티커는 JSONField).

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite)에서 `ruff format`, `ruff check`, `mypy .`, `manage.py check`, `makemigrations --check`, `manage.py test`(137개 통과), `spectacular` 스키마 경고 없음을 확인했다.
- 시각 테스트는 렌더러를 기본 `JSONRenderer`로 되돌리면 실패하는 것을 확인했다.
- PostgreSQL로는 돌리지 않았다. 변경이 DB 종류와 무관하다(이전 배포 작업에서 같은 코드가 PostgreSQL에서 통과).
- 테스트 데이터·계정 변경 없음.

## 리뷰어가 볼 곳

- `config/renderers.py`: 전역 렌더러 교체라 모든 API 응답에 영향이 간다.
- `serializers.py`의 `scale` 범위 처리(`nan`, 문자열 포함).

## 배포·마이그레이션 메모

마이그레이션 없음. 병합하면 배포 서버(`dongle-api`)가 `chore/hosting-deploy` 브랜치를 따라가므로 자동으로 다시 배포된다. 이미 저장된 편지는 `scale`이 없어 응답에서 0.18로 보인다.

## 관련 문서

- 문서 레포 `requests/1115_fe2be_sticker-scale.md`, `requests/1116_fe2be_letter-time-kst.md`
- 문서 레포 `api/letters.md`, `api/mailbox.md`, `api/common.md`
