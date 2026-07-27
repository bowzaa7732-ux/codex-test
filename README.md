# AI Cloud OS

AI Cloud OS is a secure, server-rendered FastAPI application for turning Thai or English instructions into reviewable execution plans. The included deterministic mock planner requires no API key. **No proposed file operation runs until a user explicitly approves it.**

## Features and security

- Project create, view, edit, and archive workflow; command history and audit log.
- SQLAlchemy persistence designed to accept a PostgreSQL connection URL later.
- Proposed file operations, explicit approve/reject decision, statuses, errors, and timestamps.
- Workspace confinement using resolved paths; absolute paths and traversal segments are rejected.
- No shell execution and no secrets in code or application logs.
- Planner `Protocol` makes a future AI implementation replaceable without changing the approval executor.

## Windows setup (PowerShell)

Install **Python 3.12** and Git, then open PowerShell:

```powershell
git clone <repository-url>
cd codex-test
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

If script execution is disabled, run `Set-ExecutionPolicy -Scope Process Bypass` before activating. Visit <http://localhost:8000>. Stop with **Ctrl+C**.

## macOS/Linux setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

## Docker (Windows, macOS, or Linux)

Install Docker Desktop, copy `.env.example` to `.env`, then:

```powershell
docker compose up --build
```

Named volumes preserve the database and workspaces. Run `docker compose down` to stop or `docker compose down -v` to also delete local application data.

## Test

```powershell
pytest -q
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `AI Cloud OS` | Application title |
| `DATABASE_URL` | `sqlite:///./ai_cloud_os.db` | SQLAlchemy URL; a PostgreSQL driver can be added later |
| `WORKSPACE_ROOT` | `./workspaces` | Only directory in which approved files may be written |
| `DEBUG` | `false` | Development setting; keep false in production |

## Structure

```text
app/
  models/ routes/ schemas/ services/
  static/ templates/
  config.py database.py main.py
tests/
workspaces/
Dockerfile  docker-compose.yml  requirements.txt
```

For internet-facing deployment, place the app behind a TLS reverse proxy and add your identity provider before allowing untrusted users. The initial version intentionally does not call an external AI service.
