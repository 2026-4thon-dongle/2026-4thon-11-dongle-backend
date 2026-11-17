# PR25 release: v0.3.1 (2026-11-18)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `dev` → `main`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/25

## 목적

지난 릴리스(PR22, `main` = `1e9116c`) 뒤에 `dev`에 들어온 PR24를 `main`으로 올린다. 사용자 지시로 배포 서버(`dongle-api`)가 `main`을 따라가도록 바꾸는데, 그 전에 `main`에도 Mailpit 비밀번호 설정(`MP_UI_AUTH`)이 있어야 비밀번호가 풀리지 않는다.

## 변경 사항

| PR | 내용 |
|---|---|
| PR24 | Mailpit 웹 화면·API 비밀번호(`compose.yaml` `MP_UI_AUTH: ${MAILPIT_UI_AUTH:-}`, `.env.example`, README) |
| PR26 | 이 릴리스 설명서 |

## 테스트

- PR24는 코드 변경이 없다. 로컬 docker로 Mailpit 인증(무인증·틀린 비밀번호 401, 맞는 비밀번호 200, `readyz` 통과)을 확인했고, 배포 서버(배포 #63, `359f53c`)에서도 같은 결과와 로그인 코드 메일 도착을 확인했다.
- Django 코드는 v0.3.0과 같아 테스트는 다시 돌리지 않았다(v0.3.0에서 sqlite·PostgreSQL 170개 통과).
- 원격 CI 없음. 테스트 데이터 변경 없음.
