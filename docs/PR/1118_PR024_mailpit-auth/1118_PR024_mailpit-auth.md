# PR24 chore: Mailpit 웹 화면·API에 비밀번호 걸기

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `chore/mailpit-auth` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/24

## 목적

배포 서버 Mailpit(`https://dongle-mail.zanviq.dev`)은 비밀번호 없이 열려 있어 누구나 로그인 코드를 볼 수 있었다. 2026-11-18 프론트가 공개 주소(`https://dongle.zanviq.dev`)로 배포되면서, 남의 학교 메일로 코드를 요청해 그 계정으로 로그인할 수 있게 됐다. 사용자 지시로 웹 화면과 API에 비밀번호를 건다.

## 변경 사항

- `compose.yaml`: `mailpit`에 `MP_UI_AUTH: ${MAILPIT_UI_AUTH:-}`. 값은 `사용자:비밀번호`이고 배포 서버 환경변수로 넣는다. 비우면 지금처럼 비밀번호 없이 열린다(로컬).
- `.env.example`: `MAILPIT_UI_AUTH` 추가.
- `README.md`: 「인증 메일 확인」·「홈서버 배포」의 Mailpit 설명을 비밀번호 기준으로 고침. 계정 값은 저장소에 쓰지 않고 문서 레포 `api/auth.md`에 둔다(사용자 지시).
- 사용자 이름 `dongle`은 따로 정해 준 값이 없어 정했다(가정).

## 테스트

- 로컬 docker로 `axllent/mailpit:v1.21`을 띄워 확인했다.
  - `MP_UI_AUTH`가 있으면 웹 화면과 `/api/v1/messages`가 401을 주고, 맞는 계정이면 200, 틀린 비밀번호면 401이다.
  - `/readyz`와 `/mailpit readyz`(compose healthcheck)는 비밀번호와 상관없이 통과한다.
  - 값이 비어 있으면 비밀번호 없이 200이다.
- `docker compose config`: 환경변수가 있으면 그 값이, 없으면 빈 문자열이 들어간다.
- 코드 변경이 없어 Django 검사·테스트는 생략했다. 배포 뒤 서버에서 같은 항목을 확인한다.
