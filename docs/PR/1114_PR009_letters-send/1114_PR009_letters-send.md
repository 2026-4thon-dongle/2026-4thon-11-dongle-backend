# PR9 feat: 편지 발송·배송 구간 계산

- 작성일: 2026-11-14
- 작성자: 서재민 (AI 작성)
- 브랜치: `feat/letters-send` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/9
- 관련 이슈: 해당 없음
- 관련 설계: 문서 레포 `api/letters.md`, `spec/letter.md`, `spec/mail.md`
- 작업 설계: `docs/work/feat/letters-send/1114_letters-send.md`

## 목적

`letters` 앱을 만들고 쓰기 재료 조회, 배송 시간 계산, 편지 발송(첫 편지·답장)을 구현한다(LETTER-01~09, MAIL-07).

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 앱·설정 | `apps/letters/`, `config/settings/base.py`, `.env.example` | `letters` 앱 등록, `LETTER_DEMO_MODE`(기본 False, True면 모든 편지 1분) |
| 기능 | `apps/letters/delivery.py` | 시·도 대표 좌표·인접표·섬(제주)으로 구간 판정. same_sido 60 / adjacent 180 / near 360 / far 720분 |
| 모델 | `apps/letters/models.py`, `migrations/0001` | `Conversation`(일기, host, guest, 넘긴 시각, (diary, guest) 유일), `Letter`(발송 시점 닉네임·지역 스냅숏, 구간, 본문, 편지지, 글씨체, 서명 이미지, 스티커, 우표, 발송·도착·읽음 시각, `reply_to` 1:1) |
| 기능 | `apps/letters/services.py` | 첫 편지·답장 검사, 경로 계산, 발송, 우표 지급(첫 편지·새벽·먼 길·손글씨 장인·꾸준한 편지, 답장 시 두 사람에게 첫 왕복·펜팔 친구) |
| API | `apps/letters/views.py`, `serializers.py`, `urls.py`, `config/urls.py` | `GET /api/letters/materials/`, `GET /api/letters/estimate/`, `POST /api/letters/`. Swagger 「편지」 태그 |
| 공용 | `apps/regions/serializers.py` | `RegionWithSidoSerializer`(지역 요약 + 시·도 약칭 `sido`) |
| admin | `apps/letters/admin.py` | 대화·편지 |
| 테스트 | `apps/letters/tests.py`, `testing.py` | 17개 |

## 설계·결정 반영

- 문서 레포 `api/letters.md`의 요청·응답·에러 코드대로 구현했다.
- 가정(문서 레포 `requests/1110_be2fe_spec-open-questions.md`의 「현재 가정」): 일기당 첫 편지 1통, 우표는 붙여도 없어지지 않음, 첫 왕복 우표는 두 사람 모두에게 답장 발송 때, 펜팔 친구는 같은 상대와 왕복 3회.
- 가정: 구간 판정은 시·도 단위(시·도 대표 좌표 직선거리), 제주만 섬. 받는 사람 거주지가 없으면 일기 지역을 도착지로 쓴다.
- 가정: 마무리된 대화(넘김 또는 마지막 편지 도착 후 7일)에는 답장할 수 없다(`CONVERSATION_CLOSED`).
- 차단 관계의 일기는 `visible_to`에서 빠지므로 첫 편지는 `BLOCKED`가 아니라 404가 된다. 답장은 `BLOCKED`(403).
- `draft_id`는 받기만 하고 임시저장 PR에서 연결한다.

## 디자인 영향

해당 없음

## 테스트

`feat/letters-send`(585c07d) 위에서 로컬로 돌렸다. DB는 `DATABASE_URL=sqlite:///...`로 바꿔 돌렸다.

- `python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`: 통과
- `python manage.py test`: 90개 통과 (새로 17개)
- `python manage.py makemigrations --check --dry-run`: 변경 없음
- `python manage.py spectacular`: 경고·에러 없음
- 테스트 데이터·계정 변경 없음

## 리뷰어가 볼 곳

- `services.check_reply`: 답장할 수 있는 편지는 대화의 가장 최근 편지, 도착함, 아직 답장 안 함, 마무리·넘김 아님.
- `services._grant_pair_stamps`: 받는 사람에게 준 우표는 이 응답에 나오지 않는다(그 사람의 다음 화면에서 보인다).

## 배포·마이그레이션 메모

- `letters 0001` 새 테이블 2개. 서명 이미지는 `MEDIA_ROOT/signatures/`에 저장된다(배포 저장소는 아직 미정).
- 시연 때는 `.env`에 `LETTER_DEMO_MODE=True`.

## 관련 문서

- 문서 레포 `api/letters.md`, `spec/letter.md`, `spec/mail.md`, `requests/1110_be2fe_spec-open-questions.md`
