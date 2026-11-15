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

배포 서버에서도 같은 방식으로 Mailpit을 띄우고 `EMAIL_HOST`를 Mailpit 주소로 넣는다. 시연 때는 Mailpit 웹 화면(8025)을 열어 두고 코드를 확인한다. 웹 화면은 누구나 메일을 볼 수 있으므로 외부에 열 때는 Mailpit의 `--ui-auth-file`로 비밀번호를 건다.

매주 월요일 글감 알림은 스케줄러로 `python manage.py create_weekly_prompt_notifications`를 실행한다.

편지 도착 알림은 스케줄러로 1분마다 `python manage.py notify_arrived_letters`를 실행한다. 스케줄러가 없어도 알림 목록·안 읽은 수를 조회할 때 그 사용자의 도착 알림이 만들어진다.

편지 배송 시간을 모두 1분으로 줄이려면(데모) `.env`에 `LETTER_DEMO_MODE=true`를 넣는다.

## 집 서버 시연 설정

클라우드 없이 팀원 컴퓨터에서 서버를 열어 시연할 때의 설정이다. 배포용 구성(정적 파일 서빙, gunicorn)이 아직 없으므로 `prod` 설정 대신 로컬 설정(`DEBUG=True`)과 `runserver`로 띄운다. `DEBUG=False`로 띄우면 일기 사진·손글씨 이미지(`/media/`)와 Swagger·admin 화면이 나오지 않는다.

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
