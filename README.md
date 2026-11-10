# ZENITH

Adaptive learning for Indian students in Classes 6–10. Students learn a concept, see it explained visually, practise it and show what they understand. ZENITH adapts what comes next based on their actual evidence. Teachers see who needs help and which prerequisite gaps sit behind it.

> Status: being transformed. See [docs/ZENITH_TRANSFORMATION_ASSESSMENT.md](docs/ZENITH_TRANSFORMATION_ASSESSMENT.md) for the plan and decisions, and [STATUS_REPORT.md](STATUS_REPORT.md) for current progress.

## Stack

- **Frontend:** React 19, Vite, TypeScript, CSS Modules, Dexie (offline), KaTeX, PWA.
- **Backend:** FastAPI (modular monolith), SQLAlchemy 2, Alembic, psycopg 3.
- **Data/Auth:** Supabase PostgreSQL + Auth.
- **AI:** Groq in production, LM Studio locally, behind `app/core/ai_provider.py`.
- **Hosting target:** Vercel Hobby (frontend + API as Python functions), Supabase free, Groq free.

## Local development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.production.example .env   # then fill local values
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend (the Vite dev server proxies `/api` to the backend):

```powershell
cd frontend
npm install
npm run dev
```

Backend tests need a disposable PostgreSQL:

```powershell
cd backend
docker compose -f docker-compose.test.yml up -d
$env:SETU_TEST_DATABASE_URL = "postgresql+psycopg://setu:setu_test@localhost:55432/setu_test"
.\.venv\Scripts\python.exe -m pytest -q
```

Local AI with LM Studio: set `LLM_PROVIDER=lmstudio`, `LLM_BASE_URL=http://localhost:1234/v1`, `LLM_MODEL=<loaded model id>`, `ENABLE_REMOTE_AI=true`.

## Rules

Project rules live in [AGENTS.md](AGENTS.md).
