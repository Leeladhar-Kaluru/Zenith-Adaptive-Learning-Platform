# Moving long-running work to Render: audit, recommendation, plan

Status: **proposal. Nothing in Render or in production has been created, changed or migrated.** The worker code in this repository is additive and inert until a worker process is started.

## 1. What the audit found

**Backend today**
- FastAPI app (`backend/app`), deployed as a single Vercel serverless function (`api/index.py`, `maxDuration` 30 s, region `bom1`). No process can run between requests.
- Runtime dependencies are deliberately small (`requirements.txt`: fastapi, sqlalchemy, psycopg, pydantic, httpx, PyJWT). Tools such as PyYAML, SymPy and Shapely are installed only on a laptop or CI. (This caused the 13 Nov outage when pipeline code imported two of them; fixed, with a regression test.)
- Data: Supabase PostgreSQL (schema `zenith`), Supabase Auth (JWT verified in the API), Backblaze B2 for class files, Groq for the tutor. None of this needs to move.
- Work that already does not fit serverless: the content pipeline (crawl index pages, fetch and clean pages, call a model to draft lessons, score drafts). It currently runs as a time-boxed batch (20 s) from a once-a-day Vercel Cron. A crawl or model call that takes longer is cut off, and Vercel's free plan allows only one cron run per day.
- Short work that is fine on Vercel and stays there: all student-facing requests (answers, practice, dashboard, arena, chat, tutor).

**Render account today:** one workspace ("My Workspace") holding three unrelated services (Workout-Buddy, finance-tracker, hello) on the free web-service plan. No Postgres, no Key Value (Redis). Nothing for Zenith yet.

## 2. Evaluating the options

| Option | Fit | Verdict |
|---|---|---|
| **Celery + Redis** | Industry standard. Needs a broker (Render Key Value, paid for persistence), a worker, and a scheduler (Celery beat) as separate processes; JSON serialisation of task arguments; extra moving parts to monitor. | Overkill here. Our jobs are tens to hundreds per day, I/O-bound, and their state already lives in Postgres. |
| **Postgres-backed queue worker** (recommended) | Jobs already live in `ingest_jobs` (status, attempts, requester demand). `SELECT ... FOR UPDATE SKIP LOCKED` lets several workers share a queue safely. Retries, back-off, stale-lock recovery and history are a few columns. No broker, no extra bill, one fewer thing to fail. State is visible with plain SQL. | **Chosen.** Built and tested (`app/worker.py`, migration 010). |
| Render Workflows / Cron Jobs only | Cron Jobs fit scheduled batches but each run starts cold and cannot react to a request in seconds. | Useful later for periodic maintenance; not needed now because the worker schedules its own retries. |
| Arq / RQ / Dramatiq (lighter than Celery) | Still need Redis. | Upgrade path if volume grows (see section 6). |

**Why not Redis now:** one more paid service, another secret, another failure mode, and the queue would duplicate state we already store. The switch point is concrete: if jobs exceed roughly 10 per second, or we need fan-out, rate limiting across many workers, or sub-second dispatch, add Redis with Arq or Celery. The job functions in `app/services/pipeline.py` do not depend on the queue, so that move is a wrapper change.

## 3. Target architecture

```
Browser / PWA ──► Vercel (frontend + current API)  ──►  Supabase Postgres (zenith schema), Supabase Auth, Backblaze B2
                                    │                              ▲
                                    │ INSERT ingest_jobs           │ claim with SKIP LOCKED, heartbeat, results
                                    ▼                              │
                         Render Background Worker  ─────────────────┘   (python -m app.worker)
                         crawl, fetch, extract, evaluate, draft, retry, notify
```

**Service breakdown**

| Service | Where | Why | Cost |
|---|---|---|---|
| Frontend (PWA) | Vercel (unchanged) | Static, global, free | $0 |
| API | **Phase 1: stays on Vercel.** Phase 2 (optional): Render Web Service | Student requests are short; Vercel is fast and free. Move only if cold starts, the 30 s limit or database connection counts become a problem. | $0, or about one Starter instance if moved |
| **Background worker** | **Render Background Worker (Starter)** | Runs for hours, no HTTP timeout, restarts itself if it crashes. Render has **no free tier for workers**. | One Starter instance per month (see below) |
| Database, Auth, Storage | Supabase, Backblaze (unchanged) | Preserved exactly; no data moves | existing |
| Redis / Key Value | Not used | See section 2 | $0 |

**Cost, honestly.** Render's pages disagree on the Starter price (about $6 to $7 per month per instance for 0.5 CPU and 512 MB; the workspace Hobby plan is $0). Check [render.com/pricing](https://render.com/pricing) before approving. One worker is enough for the foreseeable load, so the new monthly cost is one Starter instance. **Free web services spin down after 15 minutes idle and take about a minute to wake**, so a free instance is unsuitable for the API or the worker, and the plan is **not** to keep anything awake with pings. The worker runs continuously on a paid instance and polls the database itself.

## 4. Reliability features (built)
- **Retries:** a job that raises is retried with exponential back-off (60 s, 120 s, ... capped at 1 h) up to `max_attempts` (3), then marked `failed` and every reviewer is notified once.
- **Stale-lock recovery:** a job running more than 15 minutes with no finish goes back to the queue (or fails after its attempts).
- **Idempotent work:** importing a page twice stores one asset; drafts are guarded by an advisory lock so two workers never draft from the same page.
- **Status and logging:** each job keeps a short history (`ingest_jobs.log`); the worker writes one JSON object per line to stdout (Render's log viewer and any log drain can read it); every loop writes a heartbeat row.
- **Monitoring:** `GET /pipeline/health` (reviewers) shows worker alive or not, queue depth by status, oldest waiting job, failures in the last 24 hours. The Pipeline screen shows it. Render also alerts on failed deploys.
- **Graceful stop:** on SIGTERM (every Render deploy) the worker finishes the current job and exits.

## 5. Migration plan (needs your approval at step 3 and 6)

1. **Done in this repository (no production effect):** worker code, migration 010 (additive columns and one table), health endpoint, tests, `render.yaml` blueprint.
2. **Back up** (`python -m app.cli backup` and `verify`) and apply migration 010 to production. Additive only.
3. **Approval needed: create the Render Background Worker** from this repository (root directory `backend`, build `pip install -r requirements-worker.txt`, start `python -m app.worker`). Environment variables go only into Render's encrypted store.
4. Watch the heartbeat on the Pipeline screen and run one test request end to end.
5. Remove the Vercel cron entry once the worker has run for a day (the cron endpoint can stay as a manual fallback).
6. **Approval needed, optional later:** move the API to a Render Web Service. Steps: deploy beside Vercel, test, set `VITE_API_BASE_URL` on the frontend, add the Render URL to the allowed origins (CORS), switch, keep Vercel as instant rollback.

**Rollback:** stop the Render worker. The queue simply waits in Postgres; the Vercel cron still works. No data is changed by stopping.

## 6. Environment variables

Worker (Render, all encrypted): `DATABASE_URL` (same as the API), `DB_SCHEMA=zenith`, `ENABLE_REMOTE_AI`, `GROQ_API_KEY`, `LLM_PROVIDER`, `BOT_CONTACT` (the Wikimedia contact, backend only), `WORKER_POLL_SECONDS` (default 5), `WORKER_NAME` (optional). The worker does **not** need `SUPABASE_SECRET_KEY`, `B2_*` or `CRON_SECRET`.

API (Vercel): unchanged. `CRON_SECRET` stays set for the fallback cron route.

Phase 2 only (API on Render): all current API variables, plus `VITE_API_BASE_URL` on the frontend.

## 7. Open decisions for you
1. Approve creating one Render Background Worker (Starter), about $6 to $7 per month, in "My Workspace".
2. Whether to move the API to Render later (not recommended until Vercel limits actually bite).
3. Production AI drafting: set `ENABLE_REMOTE_AI` and the Groq key on the worker so it can draft lessons.
