# PR44 feat: 인증 메일 실제 발송(SMTP)과 시연 주소 Mailpit 유지

- 작성일: 2026-11-19
- 작성자: 서재민 (Claude), 커밋 3개는 김민호
- 브랜치: `feat/real-email-smtp` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/44
- 관련 이슈: 없음
- 관련 설계: 해당 없음(설계 문서에 메일 발송 항목 없음)
- 작업 설계: [docs/work/feat/real-email-smtp/1119_real-email-smtp.md](../../work/feat/real-email-smtp/1119_real-email-smtp.md)

## 목적

배포 서버의 인증 코드 메일을 가입하는 사람의 실제 메일함으로 보낸다. 시연 계정(`@dongle-demo.ac.kr`)과 시연용 새 가입 주소(`@guest-demo.ac.kr`)는 실제로 없는 주소라서, 이 주소로 가는 메일만 계속 Mailpit으로 보낸다.

## 변경 사항

작성 중

## 설계·결정 반영

- 사용자 결정(2026-11-19): 실제 SMTP를 켜되 시연 주소만 Mailpit으로 보낸다.
- 김민호 님 PR41(`ff0caae`, `262e863`, `13567c7`)은 2026-11-18 main에 병합됐다가 2026-11-19 main에서 되돌려졌다. 같은 커밋을 cherry-pick해 작성자를 유지했다.

## 디자인 영향

해당 없음

## 테스트

작성 중

## 리뷰어가 볼 곳

작성 중

## 배포·마이그레이션 메모

작성 중

## 관련 문서

- 문서 레포 `api/auth.md` `POST /api/auth/email/send/`, `changes/1119_be_real-email-smtp.md`, `demo/data.md`
