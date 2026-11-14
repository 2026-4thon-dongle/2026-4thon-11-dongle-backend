# PR13 feat: 편지 임시저장과 배송 경로

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/drafts-route` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/13
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/letters.md`, `spec/letter.md`, `screens/04_letter-write.md`, `screens/07_my-page.md`
- 작업 설계: `docs/work/feat/drafts-route/1114_drafts-route.md`

## 목적

편지 임시저장(LETTER-11)과 실시간 배송 지도용 경로(LETTER-10)를 구현하고, 임시저장을 발송·피드·통계와 연결한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 모델 | `apps/letters/models.py`, `migrations/0003`, `admin.py` | `Draft`(사용자·대상당 1통, 대상은 일기 또는 받은 편지 중 하나) |
| API | `apps/letters/draft_views.py`, `draft_serializers.py` | `GET/POST /api/letters/drafts/`, `GET/DELETE /api/letters/drafts/{id}/` |
| 기능 | `apps/letters/route.py` | 경유 시·도와 진행률, 경유지 최근 일기, 편지별 지도 테마 |
| API | `apps/letters/route_views.py`, `urls.py` | `GET /api/letters/{id}/route/` |
| 연결 | `apps/letters/services.py`, `views.py` | 발송하면 `draft_id`와 같은 대상의 임시저장을 지운다 |
| 연결 | `apps/feeds/views.py`, `apps/users/serializers.py` | 피드 일기 상세 `my_draft`, 마이 페이지 `draft_count` |
| 문서 | `CLAUDE.md` | 2절 현재 단계 갱신 |
| 테스트 | `apps/letters/tests_drafts_route.py` | 9개 |

## 설계·결정 반영

- 임시저장은 명세대로 대상마다 1통이고, 다시 저장하면 덮어쓴다(새로 만들면 201, 덮어쓰면 200). 서명·스티커·우표는 저장하지 않는다.
- 내 일기 대상 임시저장은 `VALIDATION_ERROR`(400), 아직 도착하지 않았거나 내가 받지 않은 편지는 `NOT_FOUND`(404)다(가정).
- 발송하면 이어 쓴 임시저장뿐 아니라 같은 대상의 임시저장도 지운다(대상당 1통이라 남겨 둘 이유가 없음).
- 경유지는 출발·도착 시·도 대표 좌표를 잇는 직선 위에서 가장 가까운 시·도를 순서대로 고른다. 시·군 좌표가 없어 경유지는 시·도 단위다(명세 예시는 시·군). 예: 서울 → 부산은 경기, 충북, 대전, 대구.
- 경유지 `story`는 그 시·도에서 쓴 일기 중 조회자가 볼 수 있는 최신 일기(내 일기 제외)다.
- `map_theme`은 편지 id로 정한다(편지마다 고정). 지역 특성과는 관계없다(가정).
- 차단 관계면 경로도 404다. 받는 사람은 도착 전에도 경로를 볼 수 있고, 편지 내용은 주지 않는다.

## 디자인 영향

해당 없음

## 테스트

`feat/drafts-route` 위에서 로컬로 돌렸다. DB는 `DATABASE_URL=sqlite:///...`로 바꿔 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 133개 통과 (새로 9개)
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- `python manage.py spectacular`: 경고·에러 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `route.path_sidos`: 광역시 대표 좌표도 후보라서 서울 → 충남처럼 인천을 지나는 것으로 나오는 경로가 있다. 지도 연출용이라 그대로 두었다.
- 경유지마다 일기 쿼리 1번. 경유지는 많아야 5~6개다.

## 배포·마이그레이션 메모

- `letters 0003`: `Draft` 테이블 추가. 기존 데이터 영향 없음.

## 관련 문서

- 문서 레포 `api/letters.md`, `api/feed.md`, `api/users.md`, `spec/letter.md`, `screens/04_letter-write.md`, `screens/07_my-page.md`
