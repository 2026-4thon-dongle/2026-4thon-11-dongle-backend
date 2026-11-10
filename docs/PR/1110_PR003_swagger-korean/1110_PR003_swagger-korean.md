# PR3 docs: Swagger 한국어 설명 추가

- 작성일: 2026-11-10
- 작성자: 김민호 (AI 작성)
- 브랜치: `docs/swagger-korean` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/3
- 관련 이슈: 해당 없음
- 관련 설계: 해당 없음
- 작업 설계: 해당 없음 (API 동작을 바꾸지 않는 문서화 작업이라 작업 설계 문서를 쓰지 않았다)

## 목적

FE가 `/api/docs/`만 보고 API를 붙일 수 있도록, 지금까지 만든 API 30개 전부에 한국어 요약·설명·에러 코드·필드 설명을 단다. 코드 동작과 응답 형식은 바꾸지 않는다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 공통 | `config/settings/base.py` | `SPECTACULAR_SETTINGS`에 API 전체 설명(인증 방법, 401, 공통 에러 형식, 페이지네이션, 시간대)과 태그 6개(인증, 내 정보, 지역, 일기, 신고·차단, 알림)의 순서·설명 추가 |
| 공통 | `config/schema.py` (신규) | 공통 에러 응답 `{code, message, errors?}`를 문서화하는 `ErrorSerializer`와 `error_response()` 추가 |
| 인증·내 정보 | `apps/users/views.py`, `serializers.py` | API별 요약·설명·상태 코드별 에러 코드, 필드 `help_text` |
| 인증 | `apps/users/auth_urls.py` | simplejwt `TokenRefreshView`를 `extend_schema_view`로 감싸 토큰 재발급 문서 추가 (refresh 회전 안내 포함) |
| 일기 | `apps/diaries/views.py`, `serializers.py` | 작성·목록·상세·수정·삭제·글감 설명, 사진 규칙, 필드 `help_text` |
| 우표 | `apps/stamps/serializers.py` | 우표 필드 `help_text` |
| 신고·차단 | `apps/moderations/views.py`, `serializers.py` | 신고·차단·차단 해제·연락처 검사 설명, 필드 `help_text` |
| 알림 | `apps/notifications/views.py`, `serializers.py` | 알림 목록·읽음·푸시 토큰 설명, 필드 `help_text` |
| 지역 | `apps/regions/views.py`, `serializers.py` | 지역 트리 설명, `can_be_hometown`/`can_be_residence` 사용법, 필드 `help_text` |

## 설계·결정 반영

- 설명에 적은 정책 값(코드 5분 만료, 재발송 60초, 5회 시도, 신고 3건 숨김, 본문 500자, 사진 5MB·JPEG/PNG/WEBP, 토큰 1시간/14일, 우표 이름)은 모두 현재 코드와 시드 마이그레이션에서 확인한 값이다.
- 모델 필드에 `help_text`를 달면 마이그레이션이 생기므로, 모델은 건드리지 않고 시리얼라이저의 필드 인자와 `extra_kwargs`로만 설명을 붙였다.
- `ErrorSerializer.errors`가 DRF `Serializer.errors` 속성과 이름이 겹쳐 mypy가 막는다. 응답 키 이름을 그대로 문서화하려고 `# type: ignore[assignment]`를 달았다. 문서 전용 클래스라 검증에 쓰지 않는다.
- 가정: Swagger UI에서 사진 파일을 직접 올려 보려면 `COMPONENT_SPLIT_REQUEST: True`가 필요하지만, 컴포넌트 이름이 `DiaryWriteRequest` 등으로 바뀌어 FE 타입 생성에 영향을 줄 수 있어 이번 PR에서는 켜지 않았다.

## 디자인 영향

해당 없음

## 테스트

`dev`(ea17e75) 위에서 로컬로 돌렸다.

- `ruff format --check .`: 통과
- `ruff check .`: 통과
- `mypy .`: 통과 (65 files)
- `python manage.py check`: 통과
- `python manage.py spectacular --validate --fail-on-warn`: 경고 없이 통과
- `python manage.py test`: 60개 통과
- 변경 전후 OpenAPI 스키마 비교: 경로 목록 동일, 기존 컴포넌트 이름 변화 없음, `Error` 컴포넌트만 추가. 30개 operation 모두 태그와 summary가 붙은 것을 확인했다.
- 테스트 데이터·계정 변경 없음.

## 리뷰어가 볼 곳

- `/api/docs/`에서 각 API 설명과 에러 코드가 실제 동작과 맞는지 (특히 인증 메일·코드 확인의 에러 코드 목록)
- `apps/users/auth_urls.py`의 `DocumentedTokenRefreshView` 감싸기 방식

## 배포·마이그레이션 메모

마이그레이션 없음. 동작 변화 없음.

## 관련 문서

해당 없음 (API 명세 문서 변경 없음)
