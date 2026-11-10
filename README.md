# ZENITH

Adaptive learning for Indian students in Classes 6–10. Students learn a concept, see it explained visually, practise it and show what they understand. ZENITH adapts what comes next based on their actual evidence. Teachers see who needs help and which prerequisite gaps sit behind it.

> Status: being transformed. See [docs/ZENITH_TRANSFORMATION_ASSESSMENT.md](docs/ZENITH_TRANSFORMATION_ASSESSMENT.md) for the plan and decisions, and [STATUS_REPORT.md](STATUS_REPORT.md) for current progress.

## Stack

- **Frontend:** React 19, Vite, TypeScript, CSS Modules, Dexie (offline), KaTeX, PWA.
- **Backend:** FastAPI (modular monolith), SQLAlchemy 2, Alembic, psycopg 3.
- **Data/Auth:** Supabase PostgreSQL + Auth.
- **AI:** Groq in production, LM Studio locally, behind `app/core/ai_provider.py`.
- **Hosting target:** Vercel Hobby (frontend + API as Python functions), Supabase free, Groq free.

## Database: Supabase only

ZENITH uses your Supabase project for everything, including development and tests. There is no local database and no Docker.

- **`zenith` schema:** the real application data. It sits beside the old SETU tables in `public`, which ZENITH never touches.
- **`zenith_test` schema:** used only by the automated tests, which wipe it on every run. `tests/conftest.py` refuses to run anywhere else.
- Migrations create the schema if it is missing: `python -m alembic upgrade head` (uses `DB_SCHEMA`, default `zenith`; it refuses `public`).

## Local development

Put your Supabase connection string (session pooler, port 5432) in `backend/.env` as `DATABASE_URL`, plus `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` and optionally `GROQ_API_KEY` with `ENABLE_REMOTE_AI=true`. Never commit this file.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head          # creates the zenith schema
.\.venv\Scripts\python.exe -m app.cli import ../content     # loads lessons as reviewable drafts
.\.venv\Scripts\python.exe -m app.cli promote you@example.com reviewer   # after you sign up
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

```powershell
cd frontend
npm install
npm run dev     # proxies /api to the backend on :8000
```

Tests (Supabase, `zenith_test` schema; about 3 minutes because of the network):

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Local AI with LM Studio: set `LLM_PROVIDER=lmstudio`, `LLM_BASE_URL=http://localhost:1234/v1`, `LLM_MODEL=<loaded model id>`.

## Backups

Supabase's free plan has no automatic backups. `.github/workflows/backup.yml` runs weekly (Sunday 20:30 UTC): it dumps the `zenith` schema, encrypts it with AES-256-GCM using your `BACKUP_KEY`, uploads it to the private Backblaze bucket and then downloads and verifies the newest file. A B2 lifecycle rule deletes backups after 60 days (`python -m app.cli retention 60`), so storage stays small. Add the GitHub secrets `BACKUP_DATABASE_URL`, `B2_KEY_ID`, `B2_APP_KEY`, `B2_BUCKET`, `BACKUP_KEY` (see docs/DEPLOY.md). Commands: `backup`, `backups`, `verify`, `restore <file|latest> <new_schema>`, `retention <days>`, `backup-key`. Keep a copy of `BACKUP_KEY` in a password manager; without it no backup can be read.

## Rules

Project rules live in [AGENTS.md](AGENTS.md).
