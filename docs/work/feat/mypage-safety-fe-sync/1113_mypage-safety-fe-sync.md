# 마이·차단·신고 프론트 mock 대조 반영

- 작성일: 2026-11-13
- 작성자: 김민호
- 브랜치: `feat/mypage-safety-fe-sync`
- 기준 커밋: `882e99f`
- 상태: 진행 중
- 관련 PR: 미정

## 지금 작업 내용

프론트 레포(`main`, 2026-11-12 기준)의 mock과 Figma 화면을 백엔드 담당 범위(AUTH·DIARY·SAFE·SET)와 대조했다. 프론트가 「mock 전용(명세에 없음)」으로 표시한 필드 중 Figma에 있고 백엔드가 줄 수 있는 것을 추가한다.

## 목표

- `GET /api/users/me/`(로그인·가입 응답의 `user` 포함)에 `school_name`이 있다. 참가 대학 메일 도메인이면 학교 약칭, 아니면 null이다.
- `GET /api/blocks/`의 `user`에 `residence`(지역 요약, 없으면 null)가 있다.
- 신고 사유 `reason` 값은 그대로 두고 라벨을 Figma 3-7 문구로 맞춘다.

## 범위

- 포함: `school_name`, 차단 목록 `user.residence`, 신고 사유 라벨, 테스트, 문서 레포 `api/users.md`·`api/safety.md`
- 제외: `stamp_total`(우표 담당, 17의 기준이 시안에서 확인 안 됨), 임시저장·우표 API(편지·우표 담당), 자주 다니던 동네(HOLD-03)

## 참고한 상위 설계

- 문서 레포 `api/users.md`, `api/safety.md`, `screens/07_my-page.md` 7-1·7-12, `screens/03_home-feed.md` 3-7
- 프론트 `src/shared/mocks/mypage.js`, `src/shared/mocks/readingDiary.js`, `docs/mypage.md`

## 작업 계획

1. `school_name` + 테스트
2. 차단 목록 `user.residence` + 테스트
3. 신고 사유 라벨 + 마이그레이션
4. 문서 레포 api 갱신

## 세부 설계

- 학교 이름은 메일 도메인 → 약칭 대응표로 구한다. 대응표는 4호선톤 참가 8개 대학만 둔다. 하위 도메인(`xxx.kookmin.ac.kr`)도 같은 학교로 본다.
- 차단 카드의 지역은 상대의 거주 지역으로 본다. 차단은 피드에서 상대 일기를 보고 하므로, 일기에 찍힌 지역(=거주 구)과 같게 보이는 쪽을 골랐다(가정).

## 확인 방법

`python manage.py check`, `ruff format --check .`, `ruff check .`, `mypy .`, `python manage.py test`

## 진행 기록

| 날짜 | 내용 |
|---|---|
| 2026-11-13 | 작업 설계 작성 |

## 결정·변경 사항과 남은 일

- 기준 브랜치 `feat/settings-prompt-figma-sync`가 아직 `dev`에 병합되지 않았다. 그 PR이 먼저 병합되어야 한다.
