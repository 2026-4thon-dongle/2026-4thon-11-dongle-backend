# PR4 chore: 로컬에서도 EMAIL_HOST가 있으면 실제 메일 발송

- 작성일: 2026-11-10
- 작성자: 김민호 (AI 작성)
- 브랜치: `chore/local-email-smtp` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/4

## 목적

로컬 개발 중에도 학교 메일로 인증 코드가 실제로 오는지 확인할 수 있게 한다. 지금까지 로컬 설정은 메일을 항상 콘솔에만 출력했다. 설정값 몇 줄만 바뀌고 파일 2개라 경미한 변경으로 보고 간소 양식을 쓴다.

## 변경 사항

- `config/settings/local.py`: `.env`에 `EMAIL_HOST`가 있으면 SMTP로 실제 발송한다(`EMAIL_PORT` 기본 587, `EMAIL_USE_TLS` 기본 True, `EMAIL_TIMEOUT` 10초로 `prod.py`와 같음). 비어 있으면 지금처럼 console 백엔드로 콘솔에 출력한다. `.env`에 SMTP 값이 없는 팀원은 동작이 바뀌지 않는다.
- `.env.example`: 위 동작 설명과 "Gmail 앱 비밀번호는 공백 없이 16자" 안내를 주석으로 추가했다.
- 가정: 발송 계정은 Gmail SMTP + 앱 비밀번호를 쓴다. 계정 정보는 커밋하지 않고 각자 `.env`에 넣는다.

## 테스트

`dev`(ea17e75) 위에서 로컬로 돌렸다.

- `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py check`: 통과
- `python manage.py test`: 60개 통과 (테스트는 Django가 메일 백엔드를 locmem으로 바꾸므로 실제 발송 없음)
- `.env`에 Gmail SMTP 값이 있을 때 `EMAIL_BACKEND`가 SMTP로, `EMAIL_HOST`를 비우면 console로 잡히는 것을 확인했다.
- Gmail SMTP 로그인 성공을 확인했다. 같은 SMTP 값으로 `POST /api/auth/email/send/`를 호출해 학교 메일(`skuniv.ac.kr`)에 인증 메일이 도착하는 것을 확인했다.
