# PR47 feat: 학교 메일이 아닌 시연용 메일 예외 허용(EXTRA_ALLOWED_EMAILS)

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude)
- 브랜치: `feat/test-email-allowlist` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/47
- 관련 이슈: 없음
- 관련 설계: 해당 없음(학교 메일 규칙은 문서 레포 `api/auth.md`)
- 작업 설계: [docs/work/feat/test-email-allowlist/1119_test-email-allowlist.md](../../work/feat/test-email-allowlist/1119_test-email-allowlist.md)

## 목적

실제 메일 발송(SMTP)을 시연하려고 팀이 만든 Gmail 주소로 가입·로그인할 수 있게 한다. 학교 메일(`ac.kr`) 규칙은 그대로 두고, 배포 서버 환경변수에 적은 주소만 예외로 받는다.

## 변경 사항

작성 중

## 설계·결정 반영

- 사용자 지시(2026-11-19): 시연용 실제 메일 두 주소만 예외로 허용한다. 주소는 저장소에 적지 않고 배포 서버 환경변수로 넣는다.

## 디자인 영향

해당 없음

## 테스트

작성 중

## 리뷰어가 볼 곳

작성 중

## 배포·마이그레이션 메모

작성 중

## 관련 문서

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`, `POST /api/auth/email/verify/`, `POST /api/auth/signup/`
