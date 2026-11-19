# PR32 fix(diaries): 휴대폰 JPEG(MPO) 일기 사진 업로드 허용 (QA 4회차)

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r04-diaries` → `dev`
- PR 링크: https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/32
- 관련 이슈: 해당 없음 (백엔드 QA 루프 4회차)
- 관련 설계: 문서 레포 `api/diaries.md` 「POST /api/diaries/」, `spec/diary.md`
- 작업 설계: [docs/work/fix/qa-r04-diaries/1118_qa-r04-diaries.md](../../work/fix/qa-r04-diaries/1118_qa-r04-diaries.md)

## 목적

MPF 정보가 든 JPEG(MPO)를 일기 사진으로 받는다.

## 변경 사항

| 구분 | 파일/모듈 | 내용 |
|---|---|---|
| 검증 | `apps/diaries/serializers.py` | `IMAGE_FORMATS`에 `MPO` 추가. MPF 정보가 든 휴대폰 JPEG를 일기 사진으로 받는다 |
| 테스트 | `apps/diaries/tests.py` | `test_accepts_phone_jpeg_with_mpf` |

## 설계·결정 반영

- 명세의 「JPEG·PNG·WEBP」에서 JPEG에 MPF 포함 JPEG(Pillow 형식 이름 `MPO`)도 들어간다고 보았다. 파일은 바꾸지 않고 그대로 저장한다.
- 편지 손글씨 이미지는 캔버스에서 만든 PNG만 받는 규칙이라 바꾸지 않았다.

## 디자인 영향

해당 없음

## 테스트

- 로컬(sqlite): `ruff format --check .`, `ruff check .`, `mypy .`, `manage.py check`, `makemigrations --check` 통과, `manage.py test` 173개 통과(이 PR에서 1개 추가).
- 재현: 로컬 서버(8100, 수정 전 코드)에서 Pillow로 만든 2장짜리 MPO 파일(`b.jpg`, `image/jpeg`)로 일기를 쓰면 400 「JPEG, PNG, WEBP 사진만 올릴 수 있습니다.」. 보통 JPEG·PNG·WEBP는 201, GIF는 400.
- PostgreSQL은 생략(모델·쿼리 변경 없음). 원격 CI 없음. 테스트 데이터 변경 없음.

## 리뷰어가 볼 곳

- `IMAGE_FORMATS`에 `MPO`를 넣어도 GIF 등 다른 형식은 그대로 400인지 (`test_rejects_bad_image`)

## 배포·마이그레이션 메모

새 마이그레이션·환경변수 없음. 배포 서버는 `main`을 따라가므로 `dev` 병합 뒤 릴리스해야 반영된다.

## 관련 문서

- 문서 레포 `api/diaries.md` 「POST /api/diaries/」, `spec/diary.md`
