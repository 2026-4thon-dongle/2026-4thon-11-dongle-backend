# PR6 feat: 마이·차단·신고 프론트 mock 대조 반영

- 작성일: 2026-11-13
- 작성자: 김민호 (AI 작성)
- 브랜치: `feat/mypage-safety-fe-sync` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/6
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/users.md`, `api/safety.md`, `screens/07_my-page.md` 7-1·7-12, `screens/03_home-feed.md` 3-7
- 작업 설계: `docs/work/feat/mypage-safety-fe-sync/1113_mypage-safety-fe-sync.md`

## 목적

프론트 `main`(2026-11-12) mock에서 「mock 전용(명세에 없음)」으로 표시된 필드 중 Figma에 있고 백엔드 담당 범위(AUTH·DIARY·SAFE·SET)에서 줄 수 있는 것을 추가한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 기능 | `apps/users/verification.py`, `serializers.py` | `school_name` 추가. 메일 도메인 → 학교 약칭 대응표(참가 8개 대학), 하위 도메인 포함, 그 밖은 null. `GET /api/users/me/`와 로그인·가입 응답의 `user`에 들어간다 |
| 기능 | `apps/moderations/serializers.py`, `views.py` | 차단 목록·차단 생성 응답의 `user`에 `residence`(RegionSerializer, null 가능) 추가. 목록 쿼리에 `select_related("blocked__residence__parent")` |
| 수정 | `apps/moderations/models.py`, `migrations/0002_report_reason_labels.py` | 신고 사유 라벨을 Figma 3-7 순서·문구로 수정. `reason` 값은 그대로 |
| 테스트 | `apps/users/tests.py`, `apps/moderations/tests.py` | 학교 약칭 대응, 차단 목록 `residence` 확인 |
| 문서 | `docs/work/...` | 작업 설계와 진행 기록 |

## 설계·결정 반영

- 문서 레포 `api/users.md`, `api/safety.md`를 같은 날 갱신했다(문서 레포 `533fb90`). 프론트 전달용 이름 차이는 문서 레포 `changes/1113_be_mypage-safety-fe-sync.md`에 정리했다.
- 가정: 차단 카드의 지역은 상대의 거주 지역이다. 차단은 피드에서 상대 일기를 보고 하므로 일기에 찍힌 지역(=거주 구)과 같게 보이는 쪽을 골랐다.
- 반영하지 않음: `stamp_total`(「5 / 17」의 17 기준 미확인), 임시저장 목록(편지 API), 자주 다니던 동네(HOLD-03).

## 디자인 영향

해당 없음

## 테스트

`feat/mypage-safety-fe-sync`(0bb6674) 위에서 로컬로 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 63개 통과
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `SCHOOL_NAMES` 도메인 목록이 맞는지. 특히 동국대(`dongguk.ac.kr`, `dgu.ac.kr`)와 숙명여대(`sm.ac.kr`). 동국대 메일이 `ac.kr`이 아니면 가입 자체가 막힌다.

## 배포·마이그레이션 메모

- `moderations 0002`는 choices 라벨만 바꾼다. DB 스키마 변경은 없다.
- 이 브랜치는 PR5(`feat/settings-prompt-figma-sync`) 위에 쌓았다. PR5를 먼저 병합해야 diff가 이 작업만 보인다.

## 관련 문서

- 문서 레포 `api/users.md`, `api/safety.md`, `changes/1113_be_mypage-safety-fe-sync.md`
