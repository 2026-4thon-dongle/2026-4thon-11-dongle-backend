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

`migrate`가 지역·우표·글감 기본 데이터도 함께 넣는다. 로컬에서는 인증 코드가 `runserver` 콘솔에 출력된다.

매주 월요일 글감 알림은 스케줄러로 `python manage.py create_weekly_prompt_notifications`를 실행한다.

## 검사

```bash
python manage.py check
ruff format --check .
ruff check .
mypy .
python manage.py test
```
