# QA 4회차: 휴대폰 JPEG(MPO) 일기 사진 업로드 허용

- 작성일: 2026-11-18
- 작성자: 서재민 (AI 작성)
- 브랜치: `fix/qa-r04-diaries`
- 기준 커밋: `213bf20`
- 상태: 진행 중
- 관련 PR: [PR32](https://github.com/2026-4thon-dongle/2026-4thon-11-dongle-backend/pull/32)

## 지금 작업 내용

백엔드 QA 루프 4회차(일기 작성·수정·삭제·공개 범위·사진)에서 찾은 문제를 고친다.

## 목표

- 여러 장 그림 정보(MPF)가 들어 있는 JPEG(Pillow가 `MPO`로 읽는 파일)를 일기 사진으로 올리면 201로 저장된다. 지금은 400 「JPEG, PNG, WEBP 사진만 올릴 수 있습니다.」가 나온다.

## 범위

- 포함: 일기 사진 형식 검사(`apps/diaries/serializers.py`), 테스트
- 제외: 편지 손글씨 이미지(PNG만 받는 규칙 그대로), HEIC 등 명세에 없는 형식

## 참고한 상위 설계

- 문서 레포 `api/diaries.md` 「POST /api/diaries/」 `image`: JPEG·PNG·WEBP, 5MB 이하
- `spec/diary.md` 「데이터·권한」: 사진은 0~1장(JPEG·PNG·WEBP, 5MB 이하)

## 작업 계획

1. 허용 형식에 `MPO`를 더한다.
2. MPO 파일 업로드 테스트를 추가한다.

## 세부 설계

- 갤럭시 등 휴대폰 카메라 사진은 JPEG 안에 MPF(Multi-Picture Format) 정보를 넣는 경우가 많고, Pillow는 이런 파일의 `format`을 `JPEG`가 아니라 `MPO`로 돌려준다. 파일 자체는 JPEG(확장자·MIME `image/jpeg`)이고 브라우저는 첫 그림을 그대로 보여 준다.
- `IMAGE_FORMATS`에 `MPO`를 넣는다. 저장하는 파일은 바꾸지 않는다.

## 확인 방법

- Pillow로 만든 2장짜리 MPO 파일을 `image`로 올리면 201, `image` URL이 채워진다.

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-18 | 작업 설계 작성. `dev`(`213bf20`)에서 분기. 로컬 서버(8100)에서 재현: MPO JPEG 업로드 400 |

## 결정·변경 사항과 남은 일

해당 없음
