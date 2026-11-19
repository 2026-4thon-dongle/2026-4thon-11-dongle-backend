# QA 1회차: 탈퇴한 계정의 토큰 재발급 500 수정

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r01-auth`
- 기준 커밋: `213bf20`
- 상태: 리뷰 중
- 관련 PR: [PR30](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/30)

## 지금 작업 내용

백엔드 QA 루프 1회차(인증)에서 찾은 문제를 고친다.

## 목표

- 탈퇴(삭제)한 계정의 refresh 토큰으로 `POST /api/auth/token/refresh/`를 부르면 500이 아니라 401 `TOKEN_NOT_VALID`가 나온다.

## 범위

- 포함: 토큰 재발급 serializer, 테스트
- 제외: 다른 인증 API 동작, 에러 문구

## 참고한 상위 설계

- 문서 레포 `api/auth.md` 「POST /api/auth/token/refresh/」: 401 `TOKEN_NOT_VALID` = 만료·무효·로그아웃된 토큰

## 작업 계획

1. simplejwt `TokenRefreshSerializer`를 감싸 사용자가 없으면 `InvalidToken`을 낸다.
2. 재발급 뷰가 이 serializer를 쓰게 한다.
3. 테스트를 추가한다.

## 세부 설계

- 원인: simplejwt 5.5.1 `TokenRefreshSerializer.validate`가 `User.objects.get(...)`을 부르는데, 탈퇴로 사용자가 없으면 `DoesNotExist`가 잡히지 않아 500이 난다.
- `apps/users/serializers.py`에 `TokenRefreshSerializer` 하위 클래스를 두고 `validate`에서 `User.DoesNotExist`를 `InvalidToken`으로 바꾼다. 공통 에러 처리기에서 401 `TOKEN_NOT_VALID`가 된다.
- `auth_urls.py`의 `DocumentedTokenRefreshView`에 `serializer_class`를 지정한다.

## 확인 방법

- 가입 → 토큰 받기 → 탈퇴 → 받은 refresh로 재발급하면 401 `TOKEN_NOT_VALID`.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100)에서 재현: 탈퇴 뒤 재발급 500(`User.DoesNotExist`) |
| 2026-11-18 | 재발급 serializer·뷰 수정과 테스트 1개. sqlite 173개 통과 |

## 결정·변경 사항과 남은 일

- 탈퇴한 계정의 access 토큰은 401 `AUTHENTICATION_FAILED`가 나온다. 명세(`api/common.md`)에 없는 코드라 문서 보완이 필요하다(QA 진행 기록 「문서 수정 필요」).
