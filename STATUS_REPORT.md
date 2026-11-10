# ZENITH Status Report

Visible product name: ZENITH. Plan and decisions: [docs/ZENITH_TRANSFORMATION_ASSESSMENT.md](docs/ZENITH_TRANSFORMATION_ASSESSMENT.md).

## Session 2026-11-10 — Phase 0 baseline and Phase 1 removal

### Changes

**Baseline**
- Branch `baseline/pre-zenith-transform` and tag `pre-zenith-transform` hold all prior work (commit `4e87a73`). Not pushed.
- Work continues on `zenith/transform`.

**Backend removed (document/RAG stack)**
- API: `api/v1/documents.py`.
- Services: `ingestion`, `extraction`, `chunking`, `retrieval`, `lesson_generator`, `pipeline_runner`, `generation_queue`.
- Runtime and storage: `worker.py`, `core/storage.py`, `models/documents.py`, `models/jobs.py`, `tessdata/`.
- The embedding methods in `ai_provider`, the embedding/pipeline/storage settings in `config`, and the dependencies PyMuPDF, python-docx, python-pptx and python-multipart.
- Docker/Render files: `Dockerfile`, `.dockerignore`, `entrypoint.sh`, `render.yaml` (hosting is now Vercel).

**Backend refactored**
- `main.py` no longer starts a background loop; the app is a plain FastAPI instance.
- `/health` is now liveness only; the new `/health/ready` checks the database and reports the AI provider.
- Learning paths are read-only legacy endpoints.
- Attempts no longer enqueue remediation lessons or coach notes.
- The doubt (tutor) sync is grounded in curriculum lessons via `library_retrieval`, otherwise general knowledge, labelled as such. Prompts contain no student identity.
- `coach_service` no longer reads document chunks; `study_plan` no longer reads documents.
- `learning_paths.document_id` is kept as a plain legacy column (no foreign key) until the approved legacy-table drop.
- `library_validator` now loads schemas from `backend/app/content/library/schemas/`. The two JSON schemas were restored from git history, because the validator silently skipped them after the research pack was deleted. A missing schema is now an error.

**Frontend removed or renamed**
- Removed: Sources page, `AddSourcePanel`, `PlanReviewDialog`, `StudyRecordPanel`, `DynamicActivityIndicator`, upload and document API code, the `/sources` route and nav link, the duplicate `/lesson/:id` route, `setu-logo.svg`.
- Renamed: `AskSetu` → `AskZenith`; Dexie DB `SetuDeskDB` → `ZenithDB`; localStorage keys `setu_*` → `zenith_*`.
- Existing browsers lose their old local offline data and session on first load (acceptable: all existing accounts are test data).

**Repo cleanup**
- Deleted old SETU reports, audits, acceptance files, test-infrastructure notes, the three `setu-v2-*` skills, the `agents/` scratch, one-off scripts, and tests that only covered removed code.
- `.gitignore` now tracks `.env.*.example` files and ignores `tsconfig.tsbuildinfo`.
- Rewrote `README.md`, `AGENTS.md` and both production env examples.

**Not touched (needs your approval)**
- Production database, storage bucket and Supabase auth users.
- Alembic migrations 001–009 (008 is live; 009 was never applied).

### Verification (commands and results)

- `backend`: `pytest -q` against a disposable Docker Postgres (`pgvector/pgvector:pg16`, with `anon` and `authenticated` roles created to mimic Supabase) → **262 passed**.
- `e2e_tests`: `pytest -q e2e_tests` → **170 passed**. These run against a mock API client, so they do not exercise a real server.
- `frontend`: `npm run build` (`tsc -b && vite build`) → passes; PWA precache 79 entries, 1,304 KiB.
- `python -m compileall -q app tests` → clean.
- OpenAPI route groups: attempts, auth, catalogue, classroom, diagnostics, doubts, health, learning-paths, library, practice, profile, rewards, study, sync, teacher, tutor. No `documents` routes.

### Tests changed on purpose

- Deleted about 25 test files and test functions that covered only the removed pipeline.
- Rewrote `test_doubt_truth.py` for the curriculum-grounded flow.
- Updated the coaching and remediation tests: remediation lessons are no longer injected, and source cards no longer exist.
- The tutor-prompt branding test now asserts ZENITH.

### Known issues carried forward

- `learning_paths.is_library`/`library_status` overload and `library_access` still allow `draft` content to be read (to be replaced in phase P2).
- Two disconnected learner models (`concept_evidence` and `bkt_states`) remain until P3.
- Library tutor retrieval and practice questions still read JSON from disk and only cover `cbse-10-math` (to be replaced in P2/P3).
- `pgvector` is still imported by historical migration 001, and the live database still has the `vector` extension and legacy document tables.
- The root-level and `docs/superpowers/` ZENITH plan and spec documents are from the earlier rebuild attempt and are superseded by the assessment.
- Not run: the Playwright browser tests in `frontend/e2e/` (they need a running stack).

### Tools used

Git, pytest, Docker (test Postgres), npm/tsc/vite, Supabase MCP (read-only), web fetch/search. Stitch MCP is unavailable.

### Next steps

1. Phase D (design research and system) and Phase 2 (content core + review engine).
2. Approval needed later for: production DB backup and legacy-table drop, deleting the 8 test auth users, and the weekly encrypted backup job.
