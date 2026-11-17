# dongle backend

4호선톤 2026 11팀(dongle) 고향 교환 펜팔 서비스의 백엔드 API 서버. Django + DRF + PostgreSQL.

협업 규칙은 [CLAUDE.md](CLAUDE.md), 문서는 [docs/](docs/README.md)를 본다.

## 로컬 실행

필요: Python 3.12, PostgreSQL

```bash
# 1. 가상환경 (Windows: py -3.12 -m venv .venv)
python3.12 -m venv .venv

# 2. 활성화 (Windows Git Bash: source .venv/Scripts/activate, PowerShell: .venv\Scripts\Activate.ps1)
source .venv/bin/activate

# 3. 의존성
pip install -r requirements-dev.txt

# 4. 환경변수: 복사 후 DATABASE_URL 등을 내 환경에 맞게 고친다
cp .env.example .env

# 5. 테이블 생성
python manage.py migrate

# 6. 실행
python manage.py runserver
```

- API 문서(Swagger): http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

`migrate`가 지역·우표·글감 기본 데이터도 함께 넣는다.

### 인증 메일 확인

실제 메일 대신 가상 메일함 [Mailpit](https://mailpit.axllent.org/)을 쓴다. 어떤 주소로 보낸 메일이든 Mailpit 웹 화면에 쌓이므로 실제 학교 메일이나 도메인 없이 `test1@skuniv.ac.kr` 같은 주소로 가입을 시험할 수 있다.

```bash
# Mailpit 실행 (둘 중 하나). SMTP 1025, 웹 화면 8025
docker run -d --name mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
brew install mailpit && mailpit
```

`.env`에 `EMAIL_HOST=localhost`, `EMAIL_PORT=1025`를 넣고 runserver를 띄운 뒤, 인증 코드를 http://localhost:8025 에서 확인한다. `EMAIL_HOST`를 비워 두면 인증 코드가 `runserver` 콘솔에 출력된다.

배포 서버에서도 같은 방식으로 Mailpit을 띄우고 `EMAIL_HOST`를 Mailpit 주소로 넣는다. 시연 때는 Mailpit 웹 화면(8025)을 열어 두고 코드를 확인한다. 웹 화면은 누구나 메일을 볼 수 있으므로 외부에 열 때는 비밀번호를 건다(Mailpit `MP_UI_AUTH`, compose에서는 환경변수 `MAILPIT_UI_AUTH`).

매주 월요일 글감 알림은 스케줄러로 `python manage.py create_weekly_prompt_notifications`를 실행한다.

편지 도착 알림은 스케줄러로 1분마다 `python manage.py notify_arrived_letters`를 실행한다. 스케줄러가 없어도 알림 목록·안 읽은 수를 조회할 때 그 사용자의 도착 알림이 만들어진다.

편지 배송 시간을 모두 1분으로 줄이려면(데모) `.env`에 `LETTER_DEMO_MODE=true`를 넣는다.

## 홈서버 배포 (TwoMES Hosting)

홈서버 호스팅 플랫폼(TwoMES Hosting)이 저장소의 `compose.yaml`을 빌드해 띄운다. `prod` 설정(`DEBUG=False`)으로 gunicorn이 돌고, 정적 파일은 whitenoise가, 업로드 이미지(`/media/`)는 Django가 준다.

| 서비스 | 하는 일 | 외부 공개 |
|---|---|---|
| `api` | gunicorn. 시작할 때 `migrate`가 지역·우표·글감 기본 데이터까지 넣는다 | `https://dongle-api.zanviq.dev` (8000) |
| `db` | PostgreSQL 17. 데이터는 `${HOSTING_DATA_DIR}/postgres` | 없음 |
| `mailpit` | 인증 메일 가상 메일함 | `https://dongle-mail.zanviq.dev` (8025). 웹 화면·API에 비밀번호(`MAILPIT_UI_AUTH`) |
| `notifier` | 60초마다 `notify_arrived_letters`. 한 시간에 한 번 한국 시간 월요일 9시 이후면 `create_weekly_prompt_notifications`(같은 주에 사용자당 한 번) | 없음 |
| `init-media` | 업로드 폴더 소유자를 맞추는 한 번짜리 | 없음 |
| `demo-seed` | `DEMO_SEED=true`일 때만 시연 데이터를 만드는 한 번짜리(아래 「시연 준비」) | 없음 |

- 프론트는 API 기본 주소 `https://dongle-api.zanviq.dev/api/`를 쓴다. Swagger는 `/api/docs/`다.
- 인증 코드는 Mailpit 화면에서 본다. 화면과 API는 `MAILPIT_UI_AUTH`(`사용자:비밀번호`)로 잠겨 있고, 계정은 팀 안에서만 공유한다(문서 레포 `api/auth.md`). 상태 확인(`/mailpit readyz`)과 api의 SMTP 발송은 비밀번호와 상관없다.
- 플랫폼 환경변수(비밀값은 저장소에 넣지 않는다): `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`(`localhost,127.0.0.1`과 API 도메인), `CORS_ALLOWED_ORIGINS`(프론트 주소를 쉼표로), `CSRF_TRUSTED_ORIGINS`(`https://API 도메인`), `LETTER_DEMO_MODE`, `MAILPIT_UI_AUTH`.
- 프론트 주소가 바뀌면 `CORS_ALLOWED_ORIGINS`에 추가하고 다시 배포한다.
- 로컬에서 같은 구성을 확인하려면 위 값을 `.env`에 넣고 `docker compose up --build`를 실행한다. 호스트 포트는 열지 않으므로 `docker compose exec api python -c ...`나 `docker compose exec mailpit ...`로 확인한다.
- 관리자 계정이 필요하면 `docker compose exec api python manage.py createsuperuser`를 실행한다(플랫폼에서는 서버에서 같은 명령).
- 주간 글감 알림은 `notifier`가 월요일(한국 시간) 9시 이후 한 시간 안에 만든다. 바로 만들려면 서버에서 `python manage.py create_weekly_prompt_notifications`를 실행한다.
- 백업: 플랫폼 백업 일정이 매일(새벽 4시), 7개 보관이다(2026-11-17 설정). 저장공간(DB 데이터·업로드 이미지)과 DB 덤프가 함께 백업된다.
- `manage.py check --deploy`(prod 설정)의 W005·W008·W021은 터널 구조 때문에 일부러 끈다. 이유는 `config/settings/prod.py` 주석에 있다.

## 시연 준비

### 시연 데이터 만들기 (`seed_demo`)

`python manage.py seed_demo`는 시연 계정 5개(`demo1`~`demo5@dongle-demo.ac.kr`)와 일기·편지·우표를 만든다. 계정과 데이터 목록은 [docs/report/1117_9756231_test-data.md](docs/report/1117_9756231_test-data.md)에 있다.

- 몇 번 실행해도 결과가 같다. 시연 계정은 그대로 두고(로그인이 유지된다) 시연 계정끼리의 데이터만 지우고 다시 만든다. 배송 중인 편지의 도착 시각도 실행한 때를 기준으로 다시 잡힌다.
- 시연 계정이 아닌 사용자의 데이터는 바꾸지 않는다. 다른 사용자가 시연 계정 일기에 편지를 보냈으면 그 대화와 일기는 남기고 「남겼습니다」라고 알린다.
- 시연 닉네임을 다른 사용자가 쓰고 있으면 아무것도 바꾸지 않고 오류로 끝난다.
- `--arrive-in 5`: 시연 중 도착할 편지(시연4 → 시연1)를 5분 뒤 도착하게 한다(기본 3분).
- `--remove`: 시연 데이터와 시연 계정을 지운다. 다른 사용자와 대화가 있는 시연 계정은 남긴다.
- 로그인은 일반 사용자와 같다. 메일 `demo1@dongle-demo.ac.kr`로 로그인 코드를 요청하고 Mailpit에서 코드를 본다.

배포 서버에는 셸이 없으므로 compose의 `demo-seed` 서비스가 실행한다.

1. 플랫폼 환경변수에 `DEMO_SEED=true`(필요하면 `DEMO_ARRIVE_IN=5`)를 넣고 다시 배포한다. 배포할 때마다 시연 데이터가 다시 만들어진다.
2. 배포 없이 다시 만들려면 `demo-seed` 컨테이너(`dongle-api-demo-seed-1`)를 다시 시작한다.
3. 시연이 끝나면 `DEMO_SEED`를 지우거나 `false`로 바꾸고 다시 배포한다. 시연 데이터는 남는다. 지우려면 서버에서 `seed_demo --remove`를 실행한다.

### 데모 모드 (편지 1분 도착)

- `LETTER_DEMO_MODE=True`면 새로 보내는 편지가 거리와 관계없이 1분 뒤 도착한다. 이미 보낸 편지의 도착 시각은 바뀌지 않는다.
- 켜기·끄기: 플랫폼 환경변수 `LETTER_DEMO_MODE`를 `True`/`False`로 바꾸고 다시 배포한다(환경변수는 다음 배포부터 반영된다). 로컬은 `.env`를 고치고 서버를 다시 띄운다.
- `seed_demo`가 만드는 배송 중 편지는 데모 모드와 관계없이 실제 구간 시간(1~12시간)으로 둬서 시연 중에 도착하지 않는다. 시연 중 도착할 편지 1통만 `--arrive-in`분 뒤 도착한다.

### 시연 확인 순서

시연 직전에 `seed_demo`를 실행(배포 서버는 `demo-seed` 재시작)한 뒤 다음 순서로 확인한다.

1. 시연1(`demo1`)로 로그인: 메일 코드 요청 → Mailpit에서 코드 확인 → 로그인
2. 피드(`GET /api/feed/hometown/`): 본가 부산 사람들의 일기(시연2, 해운대구)가 먼저 보인다
3. 우체통 새 편지(`GET /api/mailbox/new/`): 시연2의 편지 1통, 열면(`POST /api/letters/{id}/open/`) 읽음 처리
4. 대화(`GET /api/mailbox/conversations/`): 시연3과 왕복한 대화, 시연3의 다음 편지는 배송 중
5. 배송 중(`GET /api/mailbox/in-transit/`)과 경로(`GET /api/letters/{id}/route/`): 시연1 → 시연4(밤하늘 편지지, 스티커)
6. 우표첩(`GET /api/stamps/`): 우표 5개 이상, 스티커·「밤하늘」 보상 열림
7. 일기 쓰기 → 다른 시연 계정으로 그 일기에 편지 보내기: 데모 모드면 1분 뒤 도착
8. `--arrive-in`분 뒤: 시연4의 편지가 도착하고 알림(`GET /api/notifications/`)이 생긴다

## 집 서버 시연 설정 (컴퓨터에서 직접)

클라우드·호스팅 없이 팀원 컴퓨터에서 서버를 열어 시연할 때의 설정이다. 이 방식은 `prod` 설정 대신 로컬 설정(`DEBUG=True`)과 `runserver`로 띄운다. `DEBUG=False`로 `runserver`를 띄우면 일기 사진·손글씨 이미지(`/media/`)와 Swagger·admin 화면이 나오지 않는다. 상시 서버가 필요하면 위 「홈서버 배포」를 쓴다.

1. 위 「로컬 실행」과 「인증 메일 확인」대로 PostgreSQL, Mailpit, runserver를 띄운다.
2. 터널로 https 주소를 받는다. 프론트가 https에 올라가 있으면 http API는 브라우저가 막으므로 공유기 포트포워딩보다 터널을 쓴다.

   ```bash
   # 예: Cloudflare 임시 터널. 실행할 때마다 https://xxxx.trycloudflare.com 주소가 바뀐다
   cloudflared tunnel --url http://localhost:8000
   ```

3. `.env`를 시연용으로 고친다.

   ```bash
   SECRET_KEY=   # 기본값을 쓰지 말고 새로 만든 값. 이 값이 알려지면 JWT를 위조할 수 있다
   # python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
   CORS_ALLOWED_ORIGINS=https://프론트-주소   # 프론트 배포 주소와 로컬 주소를 쉼표로
   EMAIL_HOST=localhost
   EMAIL_PORT=1025
   LETTER_DEMO_MODE=True
   ```

4. 편지 도착 알림을 바로 받으려면 cron 등으로 1분마다 `python manage.py notify_arrived_letters`를 실행한다. 돌리지 않아도 알림 목록을 조회할 때 도착 알림이 만들어진다.

주의할 점은 다음과 같다.

- `DEBUG=True`라 에러가 나면 상세 내용이 외부에 보인다. 터널은 시연·테스트 때만 열어 둔다.
- 인증 코드는 그 컴퓨터의 http://localhost:8025 에서 본다. 다른 사람도 봐야 해서 8025를 외부에 열 때는 Mailpit에 `--ui-auth-file`로 비밀번호를 건다.
- 컴퓨터가 꺼지거나 잠자기에 들어가면 서버도 내려간다. 시연 날에는 잠자기를 끈다.

## 검사

```bash
python manage.py check
ruff format --check .
ruff check .
mypy .
python manage.py test
```
