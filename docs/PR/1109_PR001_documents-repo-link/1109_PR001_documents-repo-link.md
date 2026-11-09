# PR1 docs: CLAUDE.md에 문서 레포 연동 절 추가

- 작성일: 2026-11-09
- 작성자: 서재민 (AI 작성)
- 브랜치: `docs/documents-repo-link` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/1

## 목적

프론트·백엔드 공용 문서 레포(`2026-4thon-11-dongle-documents`)를 코드 작업에서 어떻게 참조하는지 CLAUDE.md에 정한다. 경미한 변경(문서만, 파일 2개)이라 간소 양식을 쓴다.

## 변경 사항

- `CLAUDE.md`: 12절 「문서 레포 연동」 추가 (문서 레포 위치, 구현 전 `api/`·`spec/` 확인, 명세에 맞춰 구현, 명세 오류는 `issues/`·`requests/`로 제안, PR 설명서에 명세 경로 기재). 기존 절은 바꾸지 않음.
- 문서 레포 위치는 기본 구조 기준 `../2026-4thon-11-dongle-documents`로 쓰고, 로컬 구조가 다르면 세션을 시작한 폴더의 CLAUDE.md 경로를 따르게 했다(가정: 팀원마다 로컬 폴더 구조가 다를 수 있음).

## 테스트

- 문서만 바꾸는 변경이라 `manage.py check`, ruff, mypy, test는 생략했다.
