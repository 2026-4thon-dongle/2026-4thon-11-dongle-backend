# PR23 docs: 릴리스 v0.3.0 설명서 추가

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `docs/release-v0.3.0` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/23

## 목적

릴리스 PR22(`dev` → `main`)의 설명서를 `dev`에 넣는다. 릴리스 PR의 머리 브랜치가 `dev`이고 `dev`에는 직접 커밋하지 않으므로, 설명서만 담은 문서 PR을 먼저 병합한다(가정: 릴리스 설명서를 넣는 방식이 README에 없어 이렇게 정했다).

## 변경 사항

- `docs/PR/1118_PR022_release-v0.3.0/1118_PR022_release-v0.3.0.md` 추가
- 이 설명서 추가

## 테스트

문서만 바꿨다. 코드 검사는 생략했다. 병합하면 배포 서버가 `dev`를 다시 배포한다(코드 변화 없음, `DEMO_SEED=true`라 시연 데이터가 다시 만들어진다).
