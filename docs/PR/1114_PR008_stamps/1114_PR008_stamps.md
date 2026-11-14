# PR8 feat: 우표첩·우표 상세·수집 보상 API

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/stamps` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/8
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/stamps.md`, `spec/stamp.md`, `screens/design-system.md` 6절
- 작업 설계: `docs/work/feat/stamps/1114_stamps.md`

## 목적

우표 20종과 수집 보상 4단계를 갖추고, 우표첩·우표 상세·수집 보상 API를 만든다(STAMP-02~05). 편지 기능이 쓸 지급 함수를 준비한다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 모델 | `apps/stamps/models.py`, `migrations/0004` | `Stamp.kind`(achievement/decoration), `Stamp.grade`(common/rare/legendary), `UserStamp.granted_with`(획득 계기 상대), `RewardSeen`(해금 모달 확인 기록) |
| 데이터 | `migrations/0005_seed_all_stamps.py` | 업적 12 + 꾸미기 8 = 20종. 기존 2종은 종류·등급만 채움 |
| 기능 | `apps/stamps/rewards.py` | 편지지 6 · 글씨체 9 · 스티커 5 카탈로그, 수집 보상 4단계(3/5/10/15) |
| 기능 | `apps/stamps/services.py` | `grant_stamps`(여러 개 지급, 10개 도달 시 「우표 수집가」 자동 지급), `grant_stamp` 호환 유지, 보상 해금 계산, `is_item_unlocked` |
| API | `apps/stamps/views.py`, `urls.py`, `serializers.py` | `GET /api/stamps/`, `GET /api/stamps/{code}/`, `GET /api/stamps/rewards/`, `POST /api/stamps/rewards/{code}/seen/`. `StampSerializer`에 `kind`, `grade` 추가 |
| 설정 | `config/urls.py`, `config/settings/base.py` | 우표 URL, Swagger 「우표」 태그 |
| admin | `apps/stamps/admin.py` | 우표 목록 필터, 운영자 지급(UserStamp) 화면 |
| 테스트 | `apps/stamps/tests.py` | 10개 |

## 설계·결정 반영

- 문서 레포 `api/stamps.md`대로 구현했다.
- 수집 보상은 DB에 저장하지 않고 보유 우표 수로 계산한다. 열린 시각은 N번째 우표를 받은 시각이다. 모달 확인 여부만 저장한다.
- 가정: 우표 No.05~12 순서, 꾸미기 우표 등급(일반)은 화면에서 확인하지 못해 목록 순서·일반으로 정했다.
- 기존 응답의 `granted_stamps`에 `kind`, `grade`가 더해진다(호환되는 추가).

## 디자인 영향

해당 없음

## 테스트

`feat/stamps`(21c020e) 위에서 로컬로 돌렸다. DB는 `DATABASE_URL=sqlite:///...`로 바꿔 돌렸다(로컬 PostgreSQL 미사용).

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 73개 통과 (새로 10개)
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- `python manage.py spectacular`: 경고·에러 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `grant_stamps`의 수집가 자동 지급. 지급한 우표가 있을 때만 확인한다.
- `StampDetailView`는 `/api/stamps/rewards/`보다 뒤에 등록되어 있어 `rewards`가 우표 코드로 잡히지 않는다.

## 배포·마이그레이션 메모

- `stamps 0004`(필드·모델 추가), `0005`(시드). 되돌리면 No.03 이후 우표가 지워진다.

## 관련 문서

- 문서 레포 `api/stamps.md`, `spec/stamp.md`, `screens/design-system.md`
