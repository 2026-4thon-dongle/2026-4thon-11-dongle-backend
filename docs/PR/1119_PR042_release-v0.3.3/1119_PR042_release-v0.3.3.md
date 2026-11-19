# PR42 release: v0.3.3 (2026-11-19)

- 작성일: 2026-11-19
- 작성자: 서재민 (AI 작성)
- 브랜치: `dev` → `main`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/42

## 목적

백엔드 QA 루프(2026-11-18, 20회차)에서 고친 PR30~36을 `main`으로 올려 배포 서버에 반영한다(사용자 지시). 배포 서버는 `main`을 따라간다.

- 버전: v0.3.2(PR28) 뒤로 PR38·PR40 릴리스는 버전 없이 병합됐다. 이번 릴리스를 v0.3.3으로 정했다(가정).
- PR40 병합 때 자동 삭제된 원격 `dev`를 `main`(`1188782`)과 같은 커밋으로 다시 만들고, `main`을 향하던 PR30~36의 대상을 `dev`로 되돌린 뒤 병합했다. PR36은 PR39(새 편지 탭)와 import 목록이 충돌해 두 이름을 모두 남겨 해결했다.

## 변경 사항

| PR | 내용 |
|---|---|
| PR30 | 탈퇴한 계정의 토큰 재발급이 500 → 401 `TOKEN_NOT_VALID` |
| PR31 | 공백 닉네임은 `INVALID_NICKNAME` |
| PR32 | 휴대폰 JPEG(MPO) 일기 사진 업로드 허용 |
| PR33 | 스티커 code·숫자(nan·inf) 검증으로 500과 잘못된 409를 400으로 |
| PR34 | 주간 글감 알림 `target_id`에 글감 id |
| PR35 | 깨진 JSON 본문은 400 `BAD_REQUEST` |
| PR36 | 대화 중 탭·게임 홈·내 일기 목록 N+1 쿼리 줄이기(응답 같음) |
| PR43 | 이 릴리스 설명서 |

- 마이그레이션 없음.

## 테스트

- PR30~36을 `dev`(`1188782`)에 모두 합친 코드로 로컬 sqlite·PostgreSQL 17 `manage.py test` 187개 통과, `ruff check`·`mypy`·`makemigrations --check` 통과.
- 배포 뒤 배포 서버에서 시연 계정으로 확인한다.
- 원격 CI 없음.
