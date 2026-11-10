# ZENITH Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the SETU repository into ZENITH: a library-first, evidence-based adaptive learning product for CBSE Class 10 Mathematics, with a real content pipeline, concept DAG, diagnostics, shadow BKT, rewards, a grounded AI tutor, and a polished student experience — without deleting existing data or breaking teacher/upload flows.

**Architecture:** Reuse `LearningPath` → `PathLesson` → `LessonVersion` → `Question` for library chapters/resources so attempts, mastery, offline packs, and teacher evidence keep working. Add a system-owned published library, a concept DAG, BKT shadow states, rewards, diagnostics, and tutor threads. The frontend becomes a route-level lazy-loaded React app with a new ZENITH design system; `/sources` preserves the old upload-first flow.

**Tech Stack:** React 19, Vite 6, TypeScript, CSS Modules, Dexie, FastAPI, SQLAlchemy, Alembic, Supabase PostgreSQL/Auth/Storage, pgvector(768), Groq/OpenAI-compatible chat, LM Studio embeddings (optional), Playwright, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-zenith-rebuild.md`

---

## Global Constraints

- Visible product name is **ZENITH** everywhere. Never “ZENITH V2”, “ZENITH 2.0”, or “SETU” in user-facing copy, titles, manifest, onboarding, or messages.
- Keep external Supabase identifiers, bucket `setu-documents`, env names `SETU_*`, localStorage key `setu_auth_token`, and IndexedDB database `SetuDeskDB` unchanged.
- Do not delete or rewrite existing users, profiles, documents, learning paths, lessons, questions, attempts, classrooms, or messages.
- No hardcoded production users, progress, subjects, boards, languages, resource counts, lessons, quizzes, classroom memberships, or analytics. Counts come from the database.
- Frontend stays React 19 + Vite + TypeScript + CSS Modules. No Tailwind v4, no shadcn.
- Backend stays FastAPI + Supabase PostgreSQL/Auth/Storage + PostgreSQL full-text + pgvector(768).
- Library content is original. `sourceRefs: []` is allowed only for library packages with `rights: "original"`. Never rehost NCERT/textbook content.
- Lesson packs are typed/versioned. A resource is publishable only when schema and semantic validation pass.
- Background generation stays durable/idempotent. Library paths must never enqueue generation jobs or inject remediation lessons.
- Offline packs, attempts, and doubts live in IndexedDB; reconnect sync is idempotent.
- Never output, log, or commit secrets. Never expose service-role/secret keys in the browser.
- Every task ends with the listed tests passing and a commit. Do not claim completion without command output.
- Actual cloud deployment is pending credentials. Only local production verification and deployment configs are in scope.

---

## Review Focus

These are the failure modes most likely to hurt a real student even though no single task’s happy-path test covers them. Each line has a test in the owning task.

1. **Cold start with no AI provider or embeddings** — Home, chapter reading, practice, and Ask Zenith must still work; the tutor returns a safe degraded answer or 503, never a blank page, fake citation, or secret. Tests: `test_tutor_works_without_embeddings`, `e2e/ask-zenith-degraded.spec.ts` (Task 15, Task 21).
2. **A non-CBSE class/board/subject** — Explore and onboarding must show an honest empty state and a working content request, never fabricated chapters or progress. Tests: `test_catalogue_empty_filters`, `e2e/empty-library.spec.ts` (Task 11, Task 17).
3. **One wrong answer** — The UI must say “early signal — confirm with practice,” not “gap” or “weak student”; prerequisite gaps require at least two evidence points. Tests: `test_one_wrong_is_not_a_gap`, `test_diagnostic_summary_early_signal` (Task 12, Task 14).
4. **Offline/reconnect duplicate submission** — The same attempt or doubt synced twice must not duplicate evidence, XP, coins, or tutor answers. Tests: `test_idempotent_offline_attempt_reward`, `test_failed_doubt_retry_does_not_duplicate` (Task 1, Task 13).
5. **Cross-student access** — Personal paths, diagnostics, rewards, and tutor threads must 404 for another student; published library content must remain readable. Tests: `test_library_authorization_matrix`, `test_tutor_threads_are_private` (Task 11, Task 15).

---

## File Structure

### Backend — create

| Path | Responsibility |
|---|---|
| `backend/app/models/library.py` | concepts, edges, chapter map, enrollment, resource progress, publication events, content requests |
| `backend/app/models/mastery.py` | BKT states and events |
| `backend/app/models/rewards.py` | student rewards, reward events, badge catalog, student badges |
| `backend/app/models/diagnostics.py` | diagnostic sessions and items |
| `backend/app/models/tutor.py` | tutor threads and messages |
| `backend/app/services/library_access.py` | one access policy for library vs personal paths |
| `backend/app/services/library_service.py` | catalogue, chapter, resource, enrollment, progress, map |
| `backend/app/services/library_validator.py` | schema + semantic content validation |
| `backend/app/services/library_seed.py` | idempotent seed/publish/rollback |
| `backend/app/services/package_redaction.py` | shared answer-key redaction |
| `backend/app/services/bkt.py` | pure BKT math |
| `backend/app/services/mastery_service.py` | rules + BKT composition, snapshots |
| `backend/app/services/prerequisite_service.py` | DAG traversal and gap detection |
| `backend/app/services/rewards_service.py` | XP, coins, levels, streaks, badges |
| `backend/app/services/diagnostic_service.py` | diagnostic plan/answer/complete/summary |
| `backend/app/services/practice_service.py` | recommendation and question selection |
| `backend/app/services/library_retrieval.py` | keyword retrieval over published packages |
| `backend/app/services/tutor_service.py` | prompt, citations, quota, persistence |
| `backend/app/api/v1/library.py` | library routes |
| `backend/app/api/v1/diagnostics.py` | diagnostic routes |
| `backend/app/api/v1/practice.py` | practice recommendation/questions |
| `backend/app/api/v1/rewards.py` | rewards routes |
| `backend/app/api/v1/tutor.py` | tutor routes |
| `backend/app/content/library/**` | manifest, chapter metadata, 20 resource packages, 4 diagnostic banks |
| `backend/alembic/versions/009_zenith_library_rewards_mastery.py` | additive schema |
| `backend/scripts/validate_library.py` | CLI validation |
| `backend/scripts/seed_library.py` | CLI seed/publish |
| `backend/scripts/publish_library.py` | rollback/archive |
| `backend/scripts/backfill_bkt.py` | replay evidence into BKT |
| `backend/scripts/compare_bkt.py` | Brier/calibration report |
| `backend/scripts/verify_library_math.py` | sympy-backed answer verification |
| `backend/scripts/seed_badges.py` | idempotent badge catalog |
| `backend/scripts/inventory_db.py` | pre-rebuild inventory |

### Backend — modify

`app/models/__init__.py`, `app/models/learning.py`, `app/core/config.py`, `app/core/ai_provider.py`, `app/core/security.py`, `app/services/attempt_service.py`, `app/services/adaptive_engine.py`, `app/services/smart_check.py`, `app/services/study_plan.py`, `app/services/learner_insights.py`, `app/services/coach_service.py`, `app/services/sync_service.py`, `app/services/retrieval.py`, `app/services/pipeline_runner.py`, `app/api/api.py`, `app/api/v1/learning_paths.py`, `app/api/v1/study.py`, `app/api/v1/attempts.py`, `app/api/v1/health.py`, `app/main.py`.

### Frontend — create

| Path | Responsibility |
|---|---|
| `frontend/src/pages/ExplorePage.tsx` | library search/filter |
| `frontend/src/pages/ChapterPage.tsx` | chapter overview + resources |
| `frontend/src/pages/MyLearningPage.tsx` | enrolled/completed/offline |
| `frontend/src/pages/PracticePage.tsx` | diagnostic and smart practice |
| `frontend/src/pages/LearningMapPage.tsx` | concept DAG |
| `frontend/src/pages/AchievementsPage.tsx` | XP, streak, badges |
| `frontend/src/pages/ProfilePage.tsx` | academic context and preferences |
| `frontend/src/pages/AskZenithPage.tsx` | tutor threads |
| `frontend/src/pages/SourcesPage.tsx` | old HomePage upload flow |
| `frontend/src/components/OnboardingFlow.tsx` | first-run flow |
| `frontend/src/components/AskZenith.tsx` | tutor drawer (rename of AskSetu) |
| `frontend/src/components/ui/*` | Button, Card, Badge, ProgressRing, EmptyState, PageHeader, Skeleton, Toast |
| `frontend/src/components/library/*` | ChapterCard, ResourceCard, ConceptChip, ProgressBar |
| `frontend/src/components/map/ConceptMap.tsx` | accessible SVG DAG |
| `frontend/src/hooks/useLibrary.ts` | library data hooks |
| `frontend/src/hooks/useRewards.ts` | rewards data hooks |
| `frontend/src/hooks/useDiagnostic.ts` | diagnostic session state |
| `frontend/src/hooks/useTutor.ts` | tutor thread state |
| `frontend/src/services/offlineLibrary.ts` | library cache helpers |
| `frontend/src/styles/zenith.css` | brand utilities and focus styles |
| `frontend/public/zenith-mark.svg`, `zenith-logo.svg` | brand assets |
| `frontend/e2e/*.spec.ts` | new flows and accessibility |

### Frontend — modify

`src/App.tsx`, `src/App.module.css`, `src/tokens.css`, `src/main.tsx`, `src/components/Navigation.tsx`, `src/components/Navigation.module.css`, `src/components/OnboardingTour.tsx` (delete/replace), `src/pages/HomePage.tsx`, `src/pages/LessonReaderPage.tsx`, `src/pages/OfflineLibraryPage.tsx`, `src/pages/DoubtQueuePage.tsx`, `src/services/api.ts`, `src/services/syncManager.ts`, `src/db/indexedDB.ts`, `src/context/AuthContext.tsx`, `index.html`, `vite.config.ts`, `package.json`.

---

## Task 0: Safety net, baseline, and branch

**Files:**
- Create: `backend/scripts/inventory_db.py`
- Create: `context/ZENITH_PRE_REBUILD_INVENTORY.md`
- Create: `backups/` dump (not committed)
- Modify: `.gitignore` only if the dump directory is not ignored

**Interfaces:**
- Consumes: existing `backend/.env` `DATABASE_URL`.
- Produces: a recorded baseline, a database backup, and branch `feat/zenith-rebuild`.

- [ ] **Step 1: Create the branch and record the baseline**

```powershell
git switch -c feat/zenith-rebuild
docker compose -f backend/docker-compose.test.yml up -d --wait
$env:SETU_TEST_DATABASE_URL='postgresql://setu:setu_test@127.0.0.1:55432/setu_test'
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected baseline on `a3473f8`: `12 failed, 179 passed, 6 skipped`. Record the exact failing test names in `STATUS_REPORT.md`.

- [ ] **Step 2: Back up the real database without printing secrets**

Load `DATABASE_URL` from `backend/.env` into the process environment, then run:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
pg_dump $env:DATABASE_URL -Fc -f "backups/zenith-pre-$stamp.dump"
```

If `pg_dump` is unavailable, use the Supabase dashboard backup/export and record that in `STATUS_REPORT.md`. Do not commit the dump.

- [ ] **Step 3: Write and run the inventory script**

`backend/scripts/inventory_db.py` connects with `SessionLocal`, runs `SELECT COUNT(*)` for every application table, and writes a Markdown table plus the current Alembic revision to `context/ZENITH_PRE_REBUILD_INVENTORY.md`. It also records duplicate checks for `(path_lesson_id, version_number)` in `lesson_versions` and `(lesson_version_id, question_key)` in `questions`; both must be zero before migration 009 adds unique constraints. It must not print `DATABASE_URL`.

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.inventory_db
```

Expected: counts match the spec audit (6 boards, 6 subjects, 4 languages, 8 profiles, 2 documents, 6 paths, 66 lessons, 528 questions, 17 attempts, 10 classrooms, 0 resources) or the current live values if data changed.

- [ ] **Step 4: Commit the safety artifacts**

```powershell
git add docs/superpowers/specs/2026-11-06-zenith-rebuild.md docs/superpowers/plans/2026-11-06-zenith-rebuild.md backend/scripts/inventory_db.py context/ZENITH_PRE_REBUILD_INVENTORY.md STATUS_REPORT.md
git commit -m "docs: record ZENITH spec, plan, and pre-rebuild baseline"
```

---

## Task 1: Repair baseline truth regressions

**Files:**
- Modify: `backend/app/services/sync_service.py`
- Modify: `backend/app/services/pipeline_runner.py`
- Test: `backend/tests/test_doubt_truth.py`, `backend/tests/test_idempotent_sync.py`, `backend/tests/test_generation_contracts.py`, `backend/tests/test_full_learning_flow.py`

**Interfaces:**
- Consumes: existing `Doubt`, `SessionLocal`, `process_job`.
- Produces: a green baseline; `sync_doubt` returns `needs_retry` after provider failure and `answered` after retry; `process_job` leaves the caller’s session usable.

- [ ] **Step 1: Confirm the failing tests**

```powershell
$env:SETU_TEST_DATABASE_URL='postgresql://setu:setu_test@127.0.0.1:55432/setu_test'
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_doubt_truth.py tests/test_idempotent_sync.py tests/test_generation_contracts.py -q
```

Expected: 12 failures matching the baseline.

- [ ] **Step 2: Persist doubt intake before external calls**

In `sync_doubt`, after `db.add(doubt)` / `db.flush()`, capture `doubt_id = doubt.id` and `db.commit()` the intake row **before** any retrieval or LLM call. On exception:

```python
db.rollback()
doubt = db.query(Doubt).filter(Doubt.id == doubt_id).first()
if doubt is not None:
    doubt.status = "needs_retry"
    doubt.last_error_code = "tutor_unavailable"
    doubt.answer_json = {...}
    db.commit()
```

This makes retries durable and keeps `alreadyExisted` true on the second call.

- [ ] **Step 3: Stop falling back to an unrelated document when no path is supplied**

Remove the “latest document” / “any ready document” fallback. Only resolve `document_id` from the explicitly supplied `path_id` (or a path selected by the caller). If no path is supplied, answer from general knowledge with `limitations: "general_knowledge"` and no retrieval call. This matches `test_general_question_with_library_but_no_path_never_consults_retrieval`.

- [ ] **Step 4: Fix the general-knowledge prompt contract**

The no-source prompt must contain the exact phrases:

- `general knowledge`
- `Never invent a page reference`

Keep the existing language preference and “under 130 words” rules. Update the `SETU Academic Tutor` strings to `ZENITH Academic Tutor` while here.

- [ ] **Step 5: Keep the caller’s session open in `process_job`**

Remove the unconditional `db.close()` at `pipeline_runner.py:241`. The caller owns the session; `process_job` already uses a fresh `SessionLocal()` for the save phase. If the worker needs to release a connection during the LLM call, add `close_session: bool = False` and pass `True` only from the worker loop, never from tests or request handlers.

- [ ] **Step 6: Run the focused tests and then the full suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_doubt_truth.py tests/test_idempotent_sync.py tests/test_generation_contracts.py tests/test_full_learning_flow.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: focused tests pass; full suite `191 passed, 6 skipped` (or more if new tests were added).

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/sync_service.py backend/app/services/pipeline_runner.py
git commit -m "fix: make doubt retries durable and keep pipeline sessions usable"
```

---

## Task 2: Brand foundation, design gate, and metadata

**Files:**
- Create: `frontend/public/zenith-mark.svg`, `frontend/public/zenith-logo.svg`, `frontend/public/pwa-192.png`, `frontend/public/pwa-512.png`, `frontend/public/apple-touch-icon.png`, `frontend/public/maskable-icon-512.png`
- Create: `docs/design/zenith-design-system.md`, `docs/design/stitch/` references
- Create: `frontend/e2e/branding.spec.ts`
- Modify: `frontend/src/tokens.css`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/src/App.module.css`, `frontend/src/main.tsx`, `frontend/package.json`, `frontend/package-lock.json`
- Modify: `backend/app/core/config.py`, `backend/app/main.py`, `AGENTS.md`
- Test: `backend/tests/test_branding.py`, `frontend/e2e/branding.spec.ts`

**Interfaces:**
- Consumes: the design direction in spec §4.
- Produces: ZENITH tokens, logo, manifest, titles, backend product identity; `APP_NAME` default `"ZENITH"`.

- [ ] **Step 1: Generate the design gate in Stitch**

Use the Stitch MCP to create a project named `ZENITH` and generate three screens: **Home**, **Explore/Chapter**, and **Practice/Learning Map**. Save screenshots or exported references under `docs/design/stitch/`. Extract only layout, hierarchy, palette, and component decisions; do not copy generated HTML. If Stitch is unavailable, document the failure and proceed with the design direction in the spec.

- [ ] **Step 2: Write the branding test**

```python
def test_root_identifies_zenith(client):
    body = client.get("/").json()
    assert body["product"] == "ZENITH"
    assert "SETU" not in str(body)

def test_openapi_identifies_zenith(client):
    assert client.get("/openapi.json").json()["info"]["title"] == "ZENITH"
```

- [ ] **Step 3: Run it to fail**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_branding.py -q
```

Expected: FAIL because the product is still SETU.

- [ ] **Step 4: Implement the brand tokens and assets**

Update `tokens.css` with the spec palette, Fraunces/Plus Jakarta/Literata/JetBrains Mono, new radii, subject accents, and focus ring. Add the summit “Z” SVG mark and wordmark. Update `index.html` title to `ZENITH — Adaptive learning for Classes 6–10`, description, theme colour `#0C6B5F`, and font links. Update `vite.config.ts` PWA `name`, `short_name`, `description`, `theme_color`, `background_color`, and icons. Generate the PNG icons from `zenith-mark.svg` with `npx @vite-pwa/assets-generator --preset minimal public/zenith-mark.svg` (add the package as a dev dependency if the CLI is unavailable). Rename the npm package to `zenith-frontend`. Update `backend/app/core/config.py` `APP_NAME="ZENITH"`, `backend/app/main.py` FastAPI title/description/root product. Update `AGENTS.md` rule 1 so future sessions use ZENITH and keep the internal compatibility identifiers documented in `docs/OPERATIONS.md`.

- [ ] **Step 5: Write the design-system note**

`docs/design/zenith-design-system.md` records palette, type scale, spacing, radii, elevation, logo usage, status colours, motion, and accessibility rules. It is the reference for later tasks.

- [ ] **Step 6: Run tests and build**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_branding.py -q
cd ..\frontend
npm run build
```

Expected: branding tests pass; build passes. Record the new chunk sizes.

- [ ] **Step 7: Commit**

```powershell
git add frontend/public frontend/src/tokens.css frontend/index.html frontend/vite.config.ts frontend/src/App.module.css frontend/src/main.tsx frontend/package.json frontend/package-lock.json backend/app/core/config.py backend/app/main.py backend/tests/test_branding.py docs/design AGENTS.md
git commit -m "feat: establish ZENITH brand, tokens, and metadata"
```

---

## Task 3: Frontend shell, API base, routing, and UI primitives

**Files:**
- Modify: `frontend/src/services/api.ts`, `frontend/src/services/syncManager.ts`
- Modify: `frontend/src/App.tsx`, `frontend/src/App.module.css`, `frontend/src/components/Navigation.tsx`, `frontend/src/components/Navigation.module.css`
- Create: `frontend/src/components/ui/Button.tsx`, `Button.module.css`, `Card.tsx`, `Card.module.css`, `Badge.tsx`, `Badge.module.css`, `ProgressRing.tsx`, `ProgressRing.module.css`, `EmptyState.tsx`, `EmptyState.module.css`, `PageHeader.tsx`, `PageHeader.module.css`, `Skeleton.tsx`, `Skeleton.module.css`, `Toast.tsx`, `Toast.module.css`
- Create: `frontend/src/pages/ComingSoonPage.tsx`
- Create: `frontend/e2e/shell.spec.ts`

**Interfaces:**
- Consumes: existing `api` client, `AuthGate`, `AuthContext`.
- Produces: `export const API_BASE: string`; `Button({variant, size, loading, icon, children, ...})`; `ProgressRing({value, size, label})`; `EmptyState({title, body, action})`; route stubs for later pages.

- [ ] **Step 1: Respect `VITE_API_BASE_URL`**

In `api.ts`, replace `const API_BASE = '/api/v1'` with:

```ts
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
```

Update `syncManager.ts` to import `API_BASE` instead of hardcoding `/api/v1`.

- [ ] **Step 2: Add lazy routes and the shell**

In `App.tsx`, wrap route elements in `React.lazy` + `Suspense` with a `PageSkeleton` built from `Skeleton`. Add routes for `/explore`, `/chapter/:slug`, `/my-learning`, `/practice`, `/map`, `/achievements`, `/profile`, `/ask`, `/sources`, and `/onboarding`, each pointing to `ComingSoonPage` until its task lands. Keep `/teacher` and `/learn/:lessonId`. Add legacy redirects: `/dashboard` → `/my-learning`, `/lesson/:lessonId` → `/learn/:lessonId`, `/doubts` → `/ask`, `/library` → `/my-learning?tab=offline`. Remove the `OnboardingTour` render from `App.tsx`; `OnboardingFlow` replaces it in Task 16.

- [ ] **Step 3: Build the navigation**

Primary student nav: Home, Explore, My Learning, Practice, Learning Map, Ask Zenith, Achievements. Profile via the avatar menu. Teacher nav: Classroom, Profile. Add a mobile bottom nav with Home, Explore, Practice, Map, Ask. Remove the dynamic “Lesson” nav item; keep a “Continue learning” CTA on Home. Brand link says ZENITH / “Adaptive learning”.

- [ ] **Step 4: Add shared UI primitives**

Implement the primitives with CSS Modules, accessible focus states, 44px targets, and reduced-motion-safe animation. `ProgressRing` uses an SVG circle and exposes `role="img"` with an `aria-label` that includes the percentage. `EmptyState` always includes a real action or an honest explanation.

- [ ] **Step 5: Write the shell test**

```ts
test('shell shows ZENITH navigation', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/ZENITH/);
  await expect(page.getByRole('link', { name: 'Explore' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Practice' })).toBeVisible();
});
```

- [ ] **Step 6: Run build and test**

```powershell
cd frontend
npm run build
npx playwright test e2e/shell.spec.ts --project=chromium
```

Expected: build passes; test passes.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src frontend/e2e/shell.spec.ts
git commit -m "feat: add ZENITH app shell, lazy routes, and UI primitives"
```

---

## Task 4: Migration 009 and models

**Files:**
- Create: `backend/alembic/versions/009_zenith_library_rewards_mastery.py`
- Create: `backend/app/models/library.py`, `mastery.py`, `rewards.py`, `diagnostics.py`, `tutor.py`
- Modify: `backend/app/models/learning.py`, `backend/app/models/__init__.py`
- Test: `backend/tests/test_zenith_schema.py`

**Interfaces:**
- Consumes: revision `008`.
- Produces: all tables/columns in spec §7; `LIBRARY_OWNER_ID` exported from `app.models.library`.

- [ ] **Step 1: Write the schema test**

```python
def test_zenith_tables_and_columns_exist(db):
    tables = set(inspect(db.bind).get_table_names())
    assert {"concepts", "concept_edges", "concept_chapters", "library_enrollments",
            "resource_progress", "bkt_states", "bkt_events", "student_rewards",
            "reward_events", "badges", "student_badges", "diagnostic_sessions",
            "diagnostic_items", "tutor_threads", "tutor_messages",
            "content_requests", "library_publication_events"} <= tables
    columns = {c["name"] for c in inspect(db.bind).get_columns("learning_paths")}
    assert {"is_library", "library_slug", "library_status", "board_id"} <= columns

def test_new_tables_have_rls_enabled(db):
    tables = (
        "concepts", "concept_edges", "concept_chapters", "library_enrollments",
        "resource_progress", "bkt_states", "bkt_events", "student_rewards",
        "reward_events", "badges", "student_badges", "diagnostic_sessions",
        "diagnostic_items", "tutor_threads", "tutor_messages",
        "content_requests", "library_publication_events",
    )
    rows = db.execute(
        text("SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(:names)"),
        {"names": list(tables)},
    ).all()
    assert len(rows) == len(tables)
    assert all(row.relrowsecurity for row in rows)
```

- [ ] **Step 2: Run it to fail**

```powershell
$env:SETU_TEST_DATABASE_URL='postgresql://setu:setu_test@127.0.0.1:55432/setu_test'
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_zenith_schema.py -q
```

Expected: FAIL because revision 009 and the tables do not exist.

- [ ] **Step 3: Implement the migration**

Add the columns and tables exactly as spec §7. Use `op.add_column` with server defaults for existing rows. Create the partial unique index on `learning_paths.library_slug WHERE library_slug IS NOT NULL`, indexes for catalogue filters, `(owner_id, idempotency_key)` on `reward_events`, `(owner_id, badge_id)` on `student_badges`, `(owner_id, lesson_id)` on `resource_progress`, `(owner_id, path_id)` on `library_enrollments`, and `(session_id, sequence)` on `diagnostic_items`. Enable RLS on every new table. Do not add permissive policies.

- [ ] **Step 4: Implement the SQLAlchemy models**

Mirror the migration. Use `UUID(as_uuid=True)` for IDs, `JSON` for JSON columns, `DateTime(timezone=True)` for timestamps. Add relationships only where they reduce query noise; do not create circular imports. Export all new models from `app/models/__init__.py`.

- [ ] **Step 5: Run migration and tests**

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/test_zenith_schema.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: schema test passes; full suite remains green.

- [ ] **Step 6: Commit**

```powershell
git add backend/alembic/versions/009_zenith_library_rewards_mastery.py backend/app/models
git commit -m "feat: add ZENITH library, mastery, rewards, diagnostic, and tutor schema"
```

---

## Task 5: Library contracts, validator, seed, and publish CLI

**Files:**
- Create: `backend/app/services/library_validator.py`, `library_seed.py`, `package_redaction.py`
- Create: `backend/scripts/__init__.py`, `scripts/validate_library.py`, `scripts/seed_library.py`, `scripts/publish_library.py`, `scripts/verify_library_math.py`
- Create or extend: `backend/requirements-dev.txt` (pytest, pytest-asyncio, sympy; Task 24 adds ruff)
- Create: `backend/tests/fixtures/library_mini/**`
- Test: `backend/tests/test_library_validator.py`, `test_library_seed.py`, `test_library_math.py`

**Interfaces:**
- Consumes: `LearningPath`, `PathLesson`, `LessonVersion`, `Question`, new library models.
- Produces:
  - `load_library(root: Path) -> LibraryBundle` (manifest plus packages keyed by `lessonId`)
  - `validate_library(root: Path) -> ValidationReport`
  - `validate_bundle(bundle: LibraryBundle) -> ValidationReport`
  - `validate_manifest_only(root: Path) -> ValidationReport`
  - `validate_chapter(bundle: LibraryBundle, library_slug: str) -> ValidationReport`
  - `verify_packages(packages: dict[str, dict]) -> list[MathIssue]`
  - `seed_library(db, bundle: LibraryBundle, *, publish: bool, actor: str = "cli") -> SeedResult`
  - `redact_answer_keys(package: dict) -> dict`
  - `ValidationReport(ok, issues, resource_count, question_count, concept_count)`
  - `SeedResult(chapters_created, chapters_updated, resources_created, resources_updated, versions_created, questions_created, published, errors)`
- `rights` is read from the manifest, not from the lesson package. `sourceRefs: []` passes only when the owning manifest entry says `rights: "original"`.

- [ ] **Step 1: Create the minimal fixture and failing validator tests**

`backend/tests/fixtures/library_mini/` contains one board/grade/subject, one chapter, one detailed lesson, one practice set, and one concept edge. Tests:

```python
def test_valid_mini_library_passes():
    report = validate_library(MINI)
    assert report.ok, report.issues
    assert report.resource_count == 2

def test_mcq_answer_must_be_an_option():
    bundle = load_library(MINI)
    bundle.packages["lesson"]["practice"][0]["answerKey"] = "not-an-option"
    report = validate_bundle(bundle)
    assert not report.ok
    assert any(issue.code == "mcq_answer_not_in_options" for issue in report.issues)

def test_prerequisite_cycle_is_rejected():
    bundle = load_library(MINI)
    bundle.manifest["concepts"][0]["prerequisites"].append(bundle.manifest["concepts"][0]["id"])
    report = validate_bundle(bundle)
    assert any(issue.code == "concept_cycle" for issue in report.issues)

def test_placeholder_text_is_rejected():
    ...
    assert any(issue.code == "placeholder_text" for issue in report.issues)
```

- [ ] **Step 2: Run to fail**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_library_validator.py -q
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement the validator**

Implement schema checks (required fields, types, max lengths), unique IDs, concept references, DAG cycle detection via Kahn’s algorithm, MCQ/numeric/short-text checks, word-count minimums, placeholder detection, and `sourceRefs: []` allowance only when `rights == "original"`. Return stable issue codes for tests.

- [ ] **Step 4: Implement the seed/publish CLI**

`seed_library` upserts by `library_slug` and `lesson_key`, creates a system owner path with `outline_json={"title": chapter_title, "chapterNumber": n, "learningOutcomes": [...], "concepts": [...]}`, sets `board_id` and `subject_id` from the manifest, writes `LessonVersion` only when the canonical JSON hash changes, inserts `Question` rows from `practice` + `checkpointTest`, records `library_publication_events`, and commits once. Every package must include `validation.checks` with at least one passing entry. `--dry-run` prints counts without writing. `publish_library --rollback <event-id>` restores the previous version’s `published_at`/`validation_status`.

- [ ] **Step 5: Implement the math verification helper**

`scripts/verify_library_math.py` reads each package’s `practice` and `checkpointTest` questions and verifies the optional `rubric.verify` object with sympy:

- `kind: "mcq"` → answer key is one of the options.
- `kind: "numeric_expression"` → `expr` evaluates to `expected` within `tolerance`.
- `kind: "equation_roots"` → each root satisfies `expr == 0` and the root count matches.
- `kind: "identity"` → `lhs - rhs` simplifies to `0`.
- `kind: "manual"` → emits a review note, not a failure.

Add `backend/tests/test_library_math.py` asserting a known-good fixture returns `[]` and a wrong root returns a `MathIssue`.

- [ ] **Step 6: Write idempotency tests**

```python
def test_seed_twice_does_not_duplicate(db):
    bundle = load_library(MINI)
    first = seed_library(db, bundle, publish=True)
    second = seed_library(db, bundle, publish=True)
    assert second.chapters_created == 0
    assert second.resources_created == 0
    assert second.versions_created == 0
    assert db.query(LearningPath).filter(LearningPath.is_library.is_(True)).count() == 1

def test_changed_content_creates_new_version(db):
    ...
    assert versions == 2
```

- [ ] **Step 7: Run tests and CLI dry run**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_library_validator.py tests/test_library_seed.py tests/test_library_math.py -q
.\.venv\Scripts\python.exe -m scripts.validate_library --root tests/fixtures/library_mini
```

Expected: tests pass; CLI reports the fixture is valid (the full library is added in later tasks).

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/library_validator.py backend/app/services/library_seed.py backend/app/services/package_redaction.py backend/scripts backend/requirements-dev.txt backend/tests/fixtures/library_mini backend/tests/test_library_validator.py backend/tests/test_library_seed.py backend/tests/test_library_math.py
git commit -m "feat: add library validation, seeding, publication, and rollback"
```

---

## Task 6: Library manifest, concepts, DAG, and diagnostic banks

**Files:**
- Create: `backend/app/content/library/manifest.json`
- Create: `backend/app/content/library/cbse-10-math/chapter.json`
- Create: `backend/app/content/library/cbse-10-math/{real-numbers,polynomials,linear-equations,quadratic-equations}/diagnostic-bank.json`
- Test: `backend/tests/test_library_manifest.py`

**Interfaces:**
- Consumes: `validate_library`, lesson-package schema.
- Produces: 4 chapter declarations, 20 resource declarations, 30 concepts (spec §6.2.1), acyclic prerequisite edges, 8 diagnostic questions per chapter.

- [ ] **Step 1: Write the manifest test**

```python
def test_manifest_has_four_chapters_and_twenty_resources():
    bundle = load_library(LIBRARY)
    assert len(bundle.manifest["chapters"]) == 4
    assert sum(len(ch["resources"]) for ch in bundle.manifest["chapters"]) == 20

def test_concept_graph_is_acyclic_and_complete():
    bundle = load_library(LIBRARY)
    assert len(bundle.manifest["concepts"]) >= 30
    assert concept_cycle(bundle.manifest) is None
    for chapter in bundle.manifest["chapters"]:
        for resource in chapter["resources"]:
            assert resource["kind"] in RESOURCE_KINDS
        assert chapter["diagnosticBank"] == f"{chapter['slug']}/diagnostic-bank.json"
```

- [ ] **Step 2: Author the manifest and chapter metadata**

Use the concept IDs and edges from spec §6/§9. Each chapter declares `slug`, `chapterNumber`, `title`, `description`, `learningOutcomes`, `concepts`, `resources` (5 entries), and `diagnosticBank`. Every chapter has a detailed lesson, worked examples, quick revision, formula sheet, and practice set. Mark all as `rights: "original"`.

- [ ] **Step 3: Author the four diagnostic banks**

Each bank is a lesson package with `lessonId` `<chapter-slug>--diagnostic-bank`, `title`, one instruction block, empty `workedExamples`, empty `practice`, 8 questions in `checkpointTest`, and non-empty `takeaways`. Tag 4 questions to foundation concepts and 4 to chapter concepts. Do not include answer keys in prompts.

- [ ] **Step 4: Run validator and tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library --manifest-only
.\.venv\Scripts\python.exe -m pytest tests/test_library_manifest.py -q
```

Expected: manifest valid; tests pass. Full package validation runs after Tasks 7–10.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/content/library backend/tests/test_library_manifest.py
git commit -m "content: add CBSE 10 maths manifest, concept DAG, and diagnostic banks"
```

---

## Task 7: Real Numbers content

**Files:**
- Create: `backend/app/content/library/cbse-10-math/real-numbers/lesson.json`, `worked-examples.json`, `quick-revision.json`, `formula-sheet.json`, `practice-set.json`
- Test: `backend/tests/test_content_real_numbers.py`

**Interfaces:**
- Consumes: manifest concept IDs `cbse-10-math--euclids-division-lemma`, `--fundamental-theorem-arithmetic`, `--hcf-and-lcm`, `--irrational-numbers`, `--decimal-expansions`, foundations `cbse-9-math--number-systems`, `--exponents-and-radicals`.
- Produces: 5 valid lesson packages with ≥12 questions.

- [ ] **Step 1: Write the content test**

```python
def test_real_numbers_packages_validate():
    bundle = load_library(LIBRARY)
    report = validate_chapter(bundle, "cbse-10-math-real-numbers")
    assert report.ok, report.issues
    assert report.resource_count == 5
    assert report.question_count >= 12

def test_real_numbers_mcq_answers_are_options():
    ...
    assert every_mcq_answer_is_an_option(packages)

def test_real_numbers_math_verification():
    assert verify_packages(packages) == []
```

- [ ] **Step 2: Author the five resources**

Detailed lesson 700–900 words with 5–7 sections, worked examples, and 3–5 takeaways. Worked examples 4–5 fully solved problems. Quick revision 300–400 words with common mistakes and 5 rapid checks. Formula sheet 150–250 words with conditions. Practice set 6–8 questions across difficulties with hints and feedback. Use `sourceRefs: []` and `validation.status: "ready"`. Add `rubric.verify` objects for numeric/equation answers so `verify_library_math.py` can check them.

- [ ] **Step 3: Run validation, math verification, and tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library
.\.venv\Scripts\python.exe -m scripts.verify_library_math --chapter cbse-10-math-real-numbers
.\.venv\Scripts\python.exe -m pytest tests/test_content_real_numbers.py -q
```

Expected: all pass; every answer key is present, every MCQ answer is an option, and sympy checks pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/content/library/cbse-10-math/real-numbers backend/tests/test_content_real_numbers.py
git commit -m "content: add original Real Numbers chapter resources"
```

---

## Task 8: Polynomials content

**Files:**
- Create: `backend/app/content/library/cbse-10-math/polynomials/lesson.json`, `worked-examples.json`, `quick-revision.json`, `formula-sheet.json`, `practice-set.json`
- Test: `backend/tests/test_content_polynomials.py`

**Interfaces:**
- Consumes: concepts `cbse-10-math--polynomials`, `--degree-and-coefficients`, `--zeros-of-a-polynomial`, `--zeros-coefficient-relations`, `--division-algorithm-polynomials`, `--factor-and-remainder-theorems`, foundations `cbse-9-math--polynomial-basics`, `--algebraic-identities`.
- Produces: 5 valid packages with ≥12 questions.

- [ ] **Step 1: Write the content test** — same shape as Task 7, with `validate_chapter(bundle, "cbse-10-math-polynomials")`, `resource_count == 5`, `question_count >= 12`, MCQ/option and sympy checks.

- [ ] **Step 2: Author the five resources** — follow the word counts and resource contracts from Task 7. Include the relationship between zeros and coefficients, division algorithm, remainder theorem, and factor theorem. Verify every root/substitution with sympy.

- [ ] **Step 3: Run validation and tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library
.\.venv\Scripts\python.exe -m scripts.verify_library_math --chapter cbse-10-math-polynomials
.\.venv\Scripts\python.exe -m pytest tests/test_content_polynomials.py -q
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/content/library/cbse-10-math/polynomials backend/tests/test_content_polynomials.py
git commit -m "content: add original Polynomials chapter resources"
```

---

## Task 9: Pair of Linear Equations content

**Files:**
- Create: `backend/app/content/library/cbse-10-math/linear-equations/lesson.json`, `worked-examples.json`, `quick-revision.json`, `formula-sheet.json`, `practice-set.json`
- Test: `backend/tests/test_content_linear_equations.py`

**Interfaces:**
- Consumes: concepts `cbse-10-math--linear-equations-two-variables`, `--graphical-method`, `--substitution-elimination`, `--consistency-of-pairs`, `--linear-word-problems`, foundations `cbse-8-math--linear-equations-one-variable`, `cbse-9-math--coordinate-geometry-basics`.
- Produces: 5 valid packages with ≥12 questions.

- [ ] **Step 1: Write the content test** — same shape, chapter slug `cbse-10-math-linear-equations`.

- [ ] **Step 2: Author the five resources** — include graphical, substitution, elimination, consistency conditions, and word problems. Use clean tables for solution cases. Verify each system’s solution by substitution.

- [ ] **Step 3: Run validation and tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library
.\.venv\Scripts\python.exe -m scripts.verify_library_math --chapter cbse-10-math-linear-equations
.\.venv\Scripts\python.exe -m pytest tests/test_content_linear_equations.py -q
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/content/library/cbse-10-math/linear-equations backend/tests/test_content_linear_equations.py
git commit -m "content: add original Linear Equations chapter resources"
```

---

## Task 10: Quadratic Equations content

**Files:**
- Create: `backend/app/content/library/cbse-10-math/quadratic-equations/lesson.json`, `worked-examples.json`, `quick-revision.json`, `formula-sheet.json`, `practice-set.json`
- Test: `backend/tests/test_content_quadratic_equations.py`

**Interfaces:**
- Consumes: concepts `cbse-10-math--quadratic-equations`, `--factorisation-method`, `--completing-the-square`, `--quadratic-formula`, `--discriminant-and-roots`, `--quadratic-word-problems`, foundations `cbse-9-math--factorisation`, `--quadratic-polynomials`.
- Produces: 5 valid packages with ≥12 questions.

- [ ] **Step 1: Write the content test** — same shape, chapter slug `cbse-10-math-quadratic-equations`.

- [ ] **Step 2: Author the five resources** — include factorisation, completing the square, formula derivation, discriminant cases, and word problems. Verify roots and discriminants with sympy.

- [ ] **Step 3: Run validation and tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library
.\.venv\Scripts\python.exe -m scripts.verify_library_math --chapter cbse-10-math-quadratic-equations
.\.venv\Scripts\python.exe -m pytest tests/test_content_quadratic_equations.py -q
```

- [ ] **Step 4: Seed the full library and verify counts**

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_library --publish
.\.venv\Scripts\python.exe -m pytest tests/test_library_seed.py tests/test_library_manifest.py -q
```

Expected: 4 chapters, 20 visible resources, 4 hidden diagnostic banks, ≥60 questions.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/content/library/cbse-10-math/quadratic-equations backend/tests/test_content_quadratic_equations.py
git commit -m "content: add original Quadratic Equations chapter resources"
```

---

## Task 11: Library APIs, access policy, enrollment, and progress

**Files:**
- Create: `backend/app/services/library_access.py`, `library_service.py`, `backend/app/api/v1/library.py`
- Modify: `backend/app/api/api.py`, `backend/app/api/v1/attempts.py`, `backend/app/api/v1/study.py`, `backend/app/api/v1/learning_paths.py`, `backend/app/services/attempt_service.py`, `backend/app/services/study_plan.py`, `backend/app/services/smart_check.py`, `backend/app/services/coach_service.py`, `backend/app/core/security.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_library_api.py`, `test_library_authorization.py`, `test_library_attempts.py`

**Interfaces:**
- Consumes: seeded library, `redact_answer_keys`, `LearningPath.is_library`.
- Produces:
  - `get_optional_user_id(authorization: str | None) -> uuid.UUID | None`
  - `list_catalogue(db, *, board_id, grade, subject_id, query, limit, offset, owner_id: uuid.UUID | None) -> dict`
  - `get_chapter(db, slug, owner_id: uuid.UUID | None) -> dict`
  - `get_resource(db, lesson_id, owner_id: uuid.UUID | None) -> dict`
  - `get_concept(db, concept_id, owner_id: uuid.UUID | None) -> dict`
  - `enroll(db, owner_id, slug) -> dict`
  - `list_my_library(db, owner_id) -> dict`
  - `update_progress(db, owner_id, lesson_id, *, status, percent, position) -> dict`
  - `request_content(db, owner_id, *, board_id, grade, subject_id, note) -> dict`
  - `get_map(db, slug, owner_id: uuid.UUID | None) -> dict`
  - `can_read_path(path, user_id) -> bool`, `resolve_readable_lesson(...)`, `require_readable_path(...)`
  - pytest fixture `seeded_library(db)` that loads and publishes the full library for the current test.

- [ ] **Step 1: Write the API tests**

```python
def test_catalogue_lists_only_published_library(client, seeded_library):
    body = client.get("/api/v1/library/catalogue").json()
    assert body["total"] == 4
    assert {item["slug"] for item in body["items"]} == {...}

def test_catalogue_filters_by_grade_and_subject(client, seeded_library):
    assert client.get("/api/v1/library/catalogue?grade=9").json()["total"] == 0
    assert client.get("/api/v1/library/catalogue?grade=10&subject_id=mathematics").json()["total"] == 4

def test_catalogue_empty_filters_are_honest(client, seeded_library):
    body = client.get("/api/v1/library/catalogue?grade=6&subject_id=science").json()
    assert body["items"] == []
    assert body["total"] == 0

def test_catalogue_and_chapter_are_public(client, seeded_library):
    assert client.get("/api/v1/library/catalogue").status_code == 200
    assert client.get("/api/v1/library/chapters/cbse-10-math-real-numbers").status_code == 200

def test_resource_redacts_answer_keys(client, seeded_library):
    body = client.get(f"/api/v1/library/resources/{lesson_id}").json()
    assert "answerKey" not in json.dumps(body)

def test_library_attempt_is_allowed_for_any_student(client, seeded_library, student_headers):
    response = client.post("/api/v1/attempts", headers=student_headers, json={...})
    assert response.status_code == 200

def test_library_attempt_never_injects_remediation(client, seeded_library, student_headers):
    before = db.query(PathLesson).count()
    ...
    assert db.query(PathLesson).count() == before

def test_library_authorization_matrix(client, seeded_library, student_headers, other_student_headers):
    # Published library: readable by any authenticated student.
    assert client.get("/api/v1/library/chapters/cbse-10-math-real-numbers", headers=other_student_headers).status_code == 200
    # Personal path: only its owner.
    personal_path = create_personal_path(db, owner_id=student_id)
    assert client.get(f"/api/v1/learning-paths/{personal_path.id}", headers=other_student_headers).status_code == 404
    # Draft library: never visible.
    draft = create_draft_library_path(db)
    assert client.get(f"/api/v1/library/chapters/{draft.library_slug}").status_code == 404

def test_concept_and_content_request(client, seeded_library, student_headers):
    concept = client.get("/api/v1/library/concepts/cbse-10-math--hcf-and-lcm").json()
    assert concept["label"] == "HCF and LCM"
    first = client.post("/api/v1/library/requests", headers=student_headers, json={"boardId": "cbse", "grade": 6, "subjectId": "science"})
    second = client.post(...)
    assert first.status_code == 200 and second.status_code == 200
    assert db.query(ContentRequest).count() == 1
```

- [ ] **Step 2: Run to fail** — `pytest tests/test_library_api.py tests/test_library_authorization.py tests/test_library_attempts.py -q`.

- [ ] **Step 3: Implement the access policy and optional auth**

Add `get_optional_user_id` to `app/core/security.py`: verify a bearer token when present, return `None` for anonymous callers, and never raise for a missing token. `can_read_path` returns true for a published library path to any authenticated user, and for a personal path only to its owner. Draft/archived library paths are false. Replace owner-only checks in attempt, study, learning-path detail, smart-check, and coach paths. In `grade_and_record_attempt`, allow library paths and guard remediation with `and not path.is_library`.

- [ ] **Step 4: Implement the library service and routes**

Only published paths and ready versions are visible. Exclude `resource_kind='diagnostic_bank'` from chapter resources. Compute progress from `resource_progress` and enrollment; return `progress: null` for anonymous callers. `get_map` returns nodes/edges with `layer` and `order` computed by longest-path topological layering; include foundation prerequisites. Add `GET /library/concepts/{concept_id}` and idempotent `POST /library/requests`. Add the `seeded_library` fixture to `tests/conftest.py` using `seed_library(db, load_library(LIBRARY), publish=True)`.

- [ ] **Step 5: Add enrollment/progress tests**

```python
def test_enroll_is_idempotent(...):
    first = client.post("/api/v1/library/chapters/cbse-10-math-real-numbers/enroll", ...)
    second = client.post(...)
    assert first.json()["enrolled"] is True
    assert second.json()["enrolled"] is True
    assert db.query(LibraryEnrollment).count() == 1

def test_progress_completion_is_idempotent(...):
    ...
    assert completed_at == second_completed_at
```

- [ ] **Step 6: Run tests and full suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_library_api.py tests/test_library_authorization.py tests/test_library_attempts.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/library_access.py backend/app/services/library_service.py backend/app/api/v1/library.py backend/app/api/api.py backend/app/services backend/tests/test_library_*.py
git commit -m "feat: expose the published library with safe access and progress"
```

---

## Task 12: BKT, mastery composition, and prerequisite gaps

**Files:**
- Create: `backend/app/services/bkt.py`, `mastery_service.py`, `prerequisite_service.py`
- Create: `backend/scripts/backfill_bkt.py`, `compare_bkt.py`
- Modify: `backend/app/services/attempt_service.py`, `backend/app/core/config.py`
- Test: `backend/tests/test_bkt.py`, `test_mastery_service.py`, `test_prerequisites.py`

**Interfaces:**
- Consumes: `ConceptEvidence`, `QuizAttempt`, `ConceptMasterySnapshot`, `BktState`, `BktEvent`.
- Produces:
  - `update_bkt(p_known, is_correct, *, score=1.0, difficulty="standard", hints_used=0, params=BKT_DEFAULTS) -> float`
  - `record_observation(db, *, owner_id, concept_id, attempt_id, is_correct, score, difficulty, hints_used) -> MasteryResult`
  - `get_mastery(db, owner_id, concept_id) -> dict`
  - `detect_gaps(db, owner_id, target_concept_id, max_depth=3) -> dict`

- [ ] **Step 1: Write exact BKT tests**

```python
def test_correct_answer_updates_to_expected_value():
    assert update_bkt(0.25, True) == pytest.approx(0.66)

def test_incorrect_answer_updates_to_expected_value():
    assert update_bkt(0.25, False) == pytest.approx(0.184)

def test_one_hint_reduces_the_update():
    assert update_bkt(0.25, True, hints_used=1) == pytest.approx(0.541)

def test_shadow_mode_keeps_rules_as_primary(monkeypatch, db):
    monkeypatch.setattr(settings, "BKT_MODE", "shadow")
    result = record_observation(...)
    assert result.primary["primaryModel"] == "rules-v1"
    assert result.shadow[0]["model"] == "bkt_v1"
```

- [ ] **Step 2: Run to fail** — `pytest tests/test_bkt.py -q`.

- [ ] **Step 3: Implement BKT and mastery composition**

Add `BKT_MODE: str = "shadow"` and `BKT_ACTIVE_MIN_EVIDENCE: int = 3` to `config.py`. Use the formulas in spec §9.1. Store `p_before`/`p_after` in `bkt_events`. In `record_observation`, add the evidence first, then update BKT, then compute rules from all evidence. In `shadow` mode the primary is rules; in `active` mode BKT becomes primary at `evidence_count >= BKT_ACTIVE_MIN_EVIDENCE`. Write the combined explanation to `concept_mastery_snapshots`. Replace `_mastery_for_concept` in `attempt_service` with `mastery_service.get_mastery`.

- [ ] **Step 4: Implement prerequisite gap detection**

Traverse incoming edges up to depth 3, compute mastery and evidence count, and return ordered gaps. `gap` requires evidence ≥ 2 and score < 0.45. One wrong with no prior evidence is `early_signal`. `unverified` for evidence < 2. Add tests:

```python
def test_one_wrong_is_not_a_gap(db):
    ... one incorrect attempt ...
    assert gap["status"] == "early_signal"

def test_two_wrongs_create_a_gap(db):
    ... two incorrect attempts ...
    assert gap["status"] == "gap"

def test_gap_order_is_foundations_first(db):
    ...
```

- [ ] **Step 5: Add backfill/compare scripts**

`backfill_bkt.py --owner <uuid>` replays `ConceptEvidence` in order and writes states/events. `compare_bkt.py` computes Brier score from `bkt_events` and prints calibration buckets. Neither runs automatically on startup.

- [ ] **Step 6: Run tests and full suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_bkt.py tests/test_mastery_service.py tests/test_prerequisites.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/bkt.py backend/app/services/mastery_service.py backend/app/services/prerequisite_service.py backend/app/services/attempt_service.py backend/app/core/config.py backend/scripts/backfill_bkt.py backend/scripts/compare_bkt.py backend/tests/test_bkt.py backend/tests/test_mastery_service.py backend/tests/test_prerequisites.py
git commit -m "feat: add shadow BKT, mastery composition, and prerequisite gaps"
```

---

## Task 13: Rewards, streaks, and badges

**Files:**
- Create: `backend/app/services/rewards_service.py`, `backend/app/api/v1/rewards.py`
- Create: `backend/app/content/badges.json`, `backend/scripts/seed_badges.py`
- Modify: `backend/app/services/attempt_service.py`, `backend/app/api/v1/study.py`, `backend/app/api/v1/attempts.py`, `backend/app/api/api.py`
- Test: `backend/tests/test_rewards.py`, `test_rewards_api.py`

**Interfaces:**
- Consumes: `QuizAttempt`, `StudyEvent`, `ConceptEvidence`, `StudentReward`, `RewardEvent`, `Badge`, `StudentBadge`.
- Produces:
  - `award_attempt(db, *, owner_id, attempt_id, is_correct, hints_used) -> RewardAward`
  - `award_resource_completed(db, *, owner_id, lesson_id, path_id) -> RewardAward`
  - `award_diagnostic_completed(db, *, owner_id, session_id) -> RewardAward`
  - `claim_daily_goal(db, *, owner_id, now=None) -> dict`
  - `get_summary(db, owner_id) -> dict`
  - `RewardAward(xp, coins, reasons, new_badges)`

- [ ] **Step 1: Write reward tests**

```python
def test_attempt_reward_is_idempotent(db):
    first = award_attempt(db, owner_id=..., attempt_id=attempt.id, is_correct=True, hints_used=0)
    second = award_attempt(db, owner_id=..., attempt_id=attempt.id, is_correct=True, hints_used=0)
    assert first.xp == 15
    assert second.xp == 0
    assert db.query(RewardEvent).filter_by(owner_id=owner_id).count() == 2  # xp + coins

def test_streak_uses_ist_days(db):
    ...
    assert streak_current == 3

def test_badge_awarded_once(db):
    ...

def test_idempotent_offline_attempt_reward(db):
    # The same sync_idempotency_key submitted twice must create one attempt,
    # one evidence row, one XP event, and one coin event.
    ...
```

- [ ] **Step 2: Run to fail** — `pytest tests/test_rewards.py -q`.

- [ ] **Step 3: Implement rewards**

Use spec §9.5 values. `touch_streak` uses `ZoneInfo("Asia/Kolkata")` and `last_activity_on`. `award_attempt` writes XP + coins with `idempotency_key=f"attempt:{attempt_id}"`. `award_resource_completed` uses `lesson_complete:{lesson_id}`. `award_diagnostic_completed` uses `diagnostic:{session_id}`. `claim_daily_goal` sums today’s `StudyEvent.seconds` against the profile goal and uses `daily_goal:{date}`. Evaluate badges after each award.

- [ ] **Step 4: Hook rewards into attempts and study events**

Add `reward` to `AttemptOutcome` and the `/attempts` response. In `record_study_event`, after commit, call `rewards_service.maybe_award_daily_goal`. Ensure idempotent sync returns the existing reward summary without new awards.

- [ ] **Step 5: Add API tests**

`GET /rewards/me` returns real values, zero for a new student; `POST /rewards/claim-daily` returns `awarded: false` with remaining seconds when the goal is unmet; badges include earned/available. Test that another user cannot read rewards.

- [ ] **Step 6: Seed badges and run tests**

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_badges
.\.venv\Scripts\python.exe -m pytest tests/test_rewards.py tests/test_rewards_api.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/rewards_service.py backend/app/api/v1/rewards.py backend/app/content/badges.json backend/scripts/seed_badges.py backend/app/services/attempt_service.py backend/app/api/v1/study.py backend/app/api/v1/attempts.py backend/app/api/api.py backend/tests/test_rewards.py backend/tests/test_rewards_api.py
git commit -m "feat: add idempotent XP, coins, streaks, and badges"
```

---

## Task 14: Diagnostics and practice recommendation

**Files:**
- Create: `backend/app/services/diagnostic_service.py`, `practice_service.py`
- Create: `backend/app/api/v1/diagnostics.py`, `backend/app/api/v1/practice.py`
- Modify: `backend/app/api/api.py`, `backend/app/api/v1/attempts.py`
- Test: `backend/tests/test_diagnostics.py`, `test_practice_recommendation.py`

**Interfaces:**
- Consumes: library questions, `grade_and_record_attempt`, `mastery_service`, `prerequisite_service`, `rewards_service`.
- Produces:
  - `start_session(db, owner_id, chapter_slug) -> dict`
  - `answer(db, owner_id, session_id, question_key, response, hints_used, elapsed_seconds) -> dict`
  - `complete(db, owner_id, session_id) -> dict`
  - `latest(db, owner_id, chapter_slug=None) -> dict`
  - `recommend_next(db, owner_id) -> dict`
  - `select_practice_questions(db, owner_id, *, chapter_slug=None, concept_id=None, count=5) -> list[dict]`

- [ ] **Step 1: Write diagnostic tests**

```python
def test_start_returns_six_core_questions_without_answers(client, seeded_library, student_headers):
    body = client.post("/api/v1/diagnostics/start", headers=student_headers, json={"chapterSlug": "cbse-10-math-real-numbers"}).json()
    assert body["progress"]["total"] == 6
    assert "answerKey" not in json.dumps(body)

def test_wrong_answer_adds_prerequisite_question(client, ...):
    ...

def test_one_wrong_is_early_signal_not_gap(client, ...):
    ...
    assert concept["status"] == "early_signal"

def test_diagnostic_summary_early_signal(client, ...):
    ...
    assert summary["confidence"] == "early_signal"

def test_complete_is_idempotent(client, ...):
    first = client.post(f"/api/v1/diagnostics/{sid}/complete", ...)
    second = client.post(...)
    assert first.json()["summary"] == second.json()["summary"]
```

- [ ] **Step 2: Run to fail** — `pytest tests/test_diagnostics.py -q`.

- [ ] **Step 3: Implement diagnostic planning and grading**

Plan 6 core questions: 2 foundation bridge + 4 chapter concepts, one per key concept, using diagnostic bank and practice set questions. On a wrong answer, append one prerequisite question up to depth 2, max 10 total. Grade through `grade_and_record_attempt` with `attempt_kind="diagnostic"`; add `diagnostic` to the allowed Literal. Store items and update the session plan. Do not expose answer keys before submission. Expire sessions after 24 hours with 410.

- [ ] **Step 4: Implement summary and recommendation**

Summary maps each concept to `secure|developing|gap|early_signal|unverified`, includes evidence counts and model names, and recommends the earliest resource for the weakest prerequisite. `recommend_next` priority: diagnostic → remediate gap → practice developing → challenge secure → explore. If evidence is missing, return `diagnostic` or `explore`, never a fabricated weak spot.

- [ ] **Step 5: Implement practice question selection**

Add `GET /api/v1/practice/questions?chapterSlug=&conceptId=&count=5`. `select_practice_questions` returns redacted question payloads with `lessonVersionId`, `questionKey`, `prompt`, `type`, `options`, `conceptIds`, `difficulty`, and `hintCount`. Prioritize weak concepts, exclude questions answered in the last 3 days, and mix difficulties. No answer keys.

- [ ] **Step 6: Run tests and full suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_diagnostics.py tests/test_practice_recommendation.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/diagnostic_service.py backend/app/services/practice_service.py backend/app/api/v1/diagnostics.py backend/app/api/v1/practice.py backend/app/api/api.py backend/app/api/v1/attempts.py backend/tests/test_diagnostics.py backend/tests/test_practice_recommendation.py
git commit -m "feat: add evidence-based diagnostics and practice recommendations"
```

---

## Task 15: AI provider abstraction, retrieval, and grounded tutor

**Files:**
- Modify: `backend/app/core/config.py`, `backend/app/core/ai_provider.py`, `backend/app/services/retrieval.py`, `backend/app/services/sync_service.py`, `backend/app/api/api.py`, `backend/app/api/v1/health.py`
- Create: `backend/app/services/library_retrieval.py`, `tutor_service.py`, `backend/app/api/v1/tutor.py`
- Test: `backend/tests/test_ai_provider_config.py`, `test_library_retrieval.py`, `test_tutor.py`, `test_tutor_quota.py`

**Interfaces:**
- Consumes: `settings`, `TutorThread`, `TutorMessage`, published library packages.
- Produces:
  - `AIProviderService.check_health() -> dict`
  - `AIProviderService.generate_chat(...)` with provider headers/timeouts/retries
  - `retrieve_library_context(db, query, *, chapter_slug=None, lesson_id=None, limit=4) -> list[dict]`
  - `ask_tutor(db, owner_id, question, *, chapter_slug=None, lesson_id=None, thread_id=None) -> dict`
  - `TutorQuotaExceeded`, `TutorUnavailable`

- [ ] **Step 1: Write provider config tests**

```python
def test_groq_uses_bearer_auth(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    provider = AIProviderService()
    assert provider._headers()["Authorization"] == "Bearer test-key"

def test_embedding_none_raises_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "none")
    with pytest.raises(EmbeddingUnavailableError, match="not configured"):
        asyncio.run(AIProviderService().get_embedding("hello"))
```

- [ ] **Step 2: Implement provider configuration and health**

Add the spec §10.1 settings. Resolve Groq base URL/model/key defaults. Add auth headers, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`. Health probes chat, skips embeddings when provider is `none`, and returns a safe `detail` without keys. Add `library.publishedChapters`/`publishedResources` counts to `/health`.

- [ ] **Step 3: Write retrieval and tutor tests**

```python
def test_library_retrieval_finds_hcf_excerpt(db, seeded_library):
    results = retrieve_library_context(db, "How do I find the HCF of two numbers?", chapter_slug="cbse-10-math-real-numbers")
    assert results
    assert "HCF" in results[0]["excerpt"] or "highest common factor" in results[0]["excerpt"].lower()

def test_tutor_citations_are_persisted(client, seeded_library, student_headers, monkeypatch):
    monkeypatch.setattr(ai_provider, "generate_chat", fake_chat)
    body = client.post("/api/v1/tutor/ask", headers=student_headers, json={"question": "Explain HCF", "chapterSlug": "cbse-10-math-real-numbers"}).json()
    assert body["citations"]
    assert body["grounded"] is True

def test_tutor_works_without_embeddings(client, ...):
    ...
    assert response.status_code in (200, 503)

def test_tutor_threads_are_private(client, student_headers, other_student_headers):
    thread_id = client.post("/api/v1/tutor/ask", headers=student_headers, json={"question": "Explain HCF"}).json()["threadId"]
    assert client.get(f"/api/v1/tutor/threads/{thread_id}", headers=other_student_headers).status_code == 404
```

- [ ] **Step 4: Implement library retrieval and tutor**

Keyword scoring over published package blocks; no embeddings required. Build the prompt with numbered excerpts and the spec §10.3 rules. Persist user/assistant messages and citations. Enforce the daily quota from `TutorMessage` count. On provider failure raise `TutorUnavailable`; API returns 503 `{detail, retryable: true}` without upstream body. Add `test_tutor_threads_are_private`.

- [ ] **Step 5: Add FTS fallback for uploaded documents**

In `retrieval_service.hybrid_search`, catch `EmbeddingUnavailableError` and run the existing full-text query only. Return `{results, insufficient_evidence, retrieval: "fts_only"}`. Do not fail the tutor because LM Studio is down.

- [ ] **Step 6: Run tests and full suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ai_provider_config.py tests/test_library_retrieval.py tests/test_tutor.py tests/test_tutor_quota.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/core/config.py backend/app/core/ai_provider.py backend/app/services/retrieval.py backend/app/services/sync_service.py backend/app/services/library_retrieval.py backend/app/services/tutor_service.py backend/app/api/v1/tutor.py backend/app/api/v1/health.py backend/app/api/api.py backend/tests/test_ai_provider_config.py backend/tests/test_library_retrieval.py backend/tests/test_tutor.py backend/tests/test_tutor_quota.py
git commit -m "feat: add provider-aware AI and grounded library tutor"
```

---

## Task 16: Frontend data layer, onboarding, and profile

**Files:**
- Modify: `frontend/src/services/api.ts`, `frontend/src/context/AuthContext.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/hooks/useLibrary.ts`, `useRewards.ts`, `useDiagnostic.ts`, `useTutor.ts`
- Create: `frontend/src/components/OnboardingFlow.tsx`, `OnboardingFlow.module.css`
- Create: `frontend/src/pages/ProfilePage.tsx`, `ProfilePage.module.css`
- Test: `frontend/e2e/onboarding.spec.ts`, `profile.spec.ts`

**Interfaces:**
- Consumes: backend APIs from Tasks 11–15.
- Produces: typed `api.getLibraryCatalogue`, `getLibraryChapter`, `getLibraryResource`, `enrollInChapter`, `getMyLibrary`, `updateResourceProgress`, `getLearningMap`, `getConcept`, `requestContent`, `startDiagnostic`, `answerDiagnostic`, `completeDiagnostic`, `getLatestDiagnostic`, `getPracticeRecommendation`, `getRewards`, `getRewardCalendar`, `getBadges`, `claimDailyReward`, `askTutor`, `getTutorThreads`, `getTutorThread`, `deleteTutorThread`.

- [ ] **Step 1: Add typed API methods and tests**

Add the interfaces from spec §8 to `api.ts`. Add a Playwright test that intercepts `/api/v1/profile/me` and verifies the onboarding form persists the selected class, board, subjects, goal, and daily minutes.

- [ ] **Step 2: Build the onboarding flow**

Four steps: name, class + board, subjects + goal, daily goal. Show a progress indicator and a “Skip for now” link. On finish, call the profile update, set `onboardingCompleted`, refresh auth, and route to `/` or `/practice?diagnostic=1` when the selected context is CBSE 10 Maths. For other contexts, show the honest library empty state and a content request action.

- [ ] **Step 3: Build Profile**

Editable academic context, goals, daily minutes, accessibility preferences (font size, reduced motion, high contrast), AI usage note, “Clear offline downloads”, and sign out. Apply preferences to `document.documentElement` via `data-*` attributes; add CSS in `zenith.css`.

- [ ] **Step 4: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/onboarding.spec.ts e2e/profile.spec.ts --project=chromium
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/services/api.ts frontend/src/context/AuthContext.tsx frontend/src/App.tsx frontend/src/hooks frontend/src/components/OnboardingFlow.tsx frontend/src/components/OnboardingFlow.module.css frontend/src/pages/ProfilePage.tsx frontend/src/pages/ProfilePage.module.css frontend/src/styles frontend/e2e/onboarding.spec.ts frontend/e2e/profile.spec.ts
git commit -m "feat: add ZENITH onboarding and profile"
```

---

## Task 17: Home, Explore, and Chapter pages

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`, `HomePage.module.css`, `frontend/src/App.tsx`
- Create: `frontend/src/pages/ExplorePage.tsx`, `ExplorePage.module.css`, `ChapterPage.tsx`, `ChapterPage.module.css`
- Create: `frontend/src/components/library/ChapterCard.tsx`, `ChapterCard.module.css`, `ResourceCard.tsx`, `ResourceCard.module.css`, `ConceptChip.tsx`, `ConceptChip.module.css`
- Test: `frontend/e2e/library.spec.ts`, `empty-library.spec.ts`

**Interfaces:**
- Consumes: `api.getMyLibrary`, `getLibraryCatalogue`, `getLibraryChapter`, `getPracticeRecommendation`, `getRewards`, `enrollInChapter`, `requestContent`.
- Produces: library-first Home; filterable Explore; chapter detail with 5 resources and concept preview.

- [ ] **Step 1: Write the library e2e test**

```ts
test('student opens a library chapter and sees five resources', async ({ page }) => {
  await page.goto('/explore');
  await page.getByRole('link', { name: /Real Numbers/ }).click();
  await expect(page.getByRole('heading', { name: 'Real Numbers' })).toBeVisible();
  await expect(page.getByTestId('resource-card')).toHaveCount(5);
  await expect(page.getByText('Founding library')).toBeVisible();
});
```

- [ ] **Step 2: Build Home**

Unauthenticated: hero with promise, sample chapter preview, sign-in CTA. Authenticated: greeting, continue-learning card, daily goal ring, streak, next-best-action card, recommended chapter, quick actions (Explore, Practice, Ask). All values come from APIs; zero states are honest.

- [ ] **Step 3: Build Explore**

Search input with 250 ms debounce, board/class/subject filters from the API, chapter cards with progress, skeleton loading, error retry, and an empty state with “Request this subject”. Never show unpublished content.

- [ ] **Step 4: Build Chapter**

Header with board/class/subject and “Founding library” label, description, outcomes, concept chips, 5 resource cards with kind/estimated minutes/progress, diagnostic CTA, and “Start learning” enrollment action. If the chapter is unavailable, show a 404-style honest state.

- [ ] **Step 5: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/library.spec.ts e2e/empty-library.spec.ts --project=chromium
```

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/pages/HomePage.tsx frontend/src/pages/HomePage.module.css frontend/src/pages/ExplorePage.tsx frontend/src/pages/ExplorePage.module.css frontend/src/pages/ChapterPage.tsx frontend/src/pages/ChapterPage.module.css frontend/src/components/library frontend/src/App.tsx frontend/e2e/library.spec.ts frontend/e2e/empty-library.spec.ts
git commit -m "feat: add library-first home, explore, and chapter pages"
```

---

## Task 18: Reader, My Learning, Sources, and offline library

**Files:**
- Modify: `frontend/src/pages/LessonReaderPage.tsx`, `LessonReaderPage.module.css`, `frontend/src/pages/OfflineLibraryPage.tsx`, `frontend/src/db/indexedDB.ts`, `frontend/src/services/syncManager.ts`, `frontend/src/App.tsx`
- Create: `frontend/src/pages/MyLearningPage.tsx`, `MyLearningPage.module.css`, `frontend/src/pages/SourcesPage.tsx`, `SourcesPage.module.css`, `frontend/src/services/offlineLibrary.ts`
- Test: `frontend/e2e/reader.spec.ts`, `offline.spec.ts`

**Interfaces:**
- Consumes: `api.getLibraryResource`, `updateResourceProgress`, `getMyLibrary`, `askTutor`, Dexie.
- Produces: resource reader with section navigation, progress, save offline, ask-about-section; My Learning tabs; `/sources` preserving the old HomePage flow; Dexie v3.

- [ ] **Step 1: Add Dexie v3**

Add `libraryResources`, `resourceProgress`, and `tutorOutbox` tables without clearing existing data. Keep `SetuDeskDB`. Add `ownerId` indexes and migration tests in Playwright (save, reload offline, reopen).

- [ ] **Step 2: Build the reader**

Support library packages: render blocks by kind, worked examples, practice CTA, takeaways, and citations-free original content. Track reading progress with throttled `PATCH /library/resources/{id}/progress`; mark complete at the end or after the checkpoint. Add “Save offline” and “Ask about this section” (prefills the tutor with the section heading and lesson ID).

- [ ] **Step 3: Build My Learning**

Tabs: In progress, Completed, Offline. Show real progress, last opened, continue button, download size, delete download. Empty states explain how to start.

- [ ] **Step 4: Move the old HomePage to `/sources`**

Copy the existing upload-first page to `SourcesPage.tsx`, update its copy to “Sources — bring your own textbook”, and keep all upload/ingest/generate flows. Remove its old home-specific hero; link back to the library.

- [ ] **Step 5: Offline sync**

Update `syncManager` to use `API_BASE`, include library attempts, and never duplicate rewards. Show pending counts in Navigation. On reconnect/focus/manual sync, flush the outbox and refresh library progress.

- [ ] **Step 6: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/reader.spec.ts e2e/offline.spec.ts --project=chromium
```

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/pages/LessonReaderPage.tsx frontend/src/pages/LessonReaderPage.module.css frontend/src/pages/OfflineLibraryPage.tsx frontend/src/pages/MyLearningPage.tsx frontend/src/pages/MyLearningPage.module.css frontend/src/pages/SourcesPage.tsx frontend/src/pages/SourcesPage.module.css frontend/src/db/indexedDB.ts frontend/src/services/syncManager.ts frontend/src/services/offlineLibrary.ts frontend/src/App.tsx frontend/e2e/reader.spec.ts frontend/e2e/offline.spec.ts
git commit -m "feat: add library reader, my learning, sources, and offline cache"
```

---

## Task 19: Practice Arena and diagnostic UI

**Files:**
- Create: `frontend/src/pages/PracticePage.tsx`, `PracticePage.module.css`
- Create: `frontend/src/components/practice/QuestionCard.tsx`, `QuestionCard.module.css`, `FeedbackPanel.tsx`, `FeedbackPanel.module.css`, `DiagnosticSummary.tsx`, `DiagnosticSummary.module.css`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/ui/Toast.tsx`
- Test: `frontend/e2e/practice.spec.ts`

**Interfaces:**
- Consumes: `api.startDiagnostic`, `answerDiagnostic`, `completeDiagnostic`, `getPracticeRecommendation`, `api.submitAttempt`.
- Produces: diagnostic flow, smart practice, weak-concept drill, mixed check, feedback, XP toast.

- [ ] **Step 1: Write the practice e2e test**

```ts
test('student answers a practice question and sees evidence-based feedback', async ({ page }) => {
  await page.goto('/practice');
  await page.getByRole('button', { name: /Start diagnostic/i }).click();
  await page.getByLabel(/your answer/i).fill('2');
  await page.getByRole('button', { name: /Submit/i }).click();
  await expect(page.getByText(/correct answer/i)).toBeVisible();
  await expect(page.getByText(/XP/)).toBeVisible();
});
```

- [ ] **Step 2: Build the Practice Arena**

Modes: Smart practice (recommendation), Chapter practice, Weak concept drill, Mixed check. Show the reason and evidence count for every recommendation. If no evidence, show “Start with a diagnostic” rather than a fabricated weak spot. Render MCQ, numeric, and short-text inputs. Disable submit while pending. Show hints with a count, feedback, explanation, and next action.

- [ ] **Step 3: Build the diagnostic flow**

Progress bar, one question at a time, no answer key in the DOM before submit, resume support, early-exit confirmation, and a summary with concept statuses, “early signal” language, recommended start, and a CTA. Award XP toast only from the server response.

- [ ] **Step 4: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/practice.spec.ts --project=chromium
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/pages/PracticePage.tsx frontend/src/pages/PracticePage.module.css frontend/src/components/practice frontend/src/components/ui/Toast.tsx frontend/src/App.tsx frontend/e2e/practice.spec.ts
git commit -m "feat: add practice arena and evidence-based diagnostics"
```

---

## Task 20: Learning Map

**Files:**
- Create: `frontend/src/pages/LearningMapPage.tsx`, `LearningMapPage.module.css`
- Create: `frontend/src/components/map/ConceptMap.tsx`, `ConceptMap.module.css`
- Test: `frontend/e2e/map.spec.ts`

**Interfaces:**
- Consumes: `api.getLearningMap(chapterSlug)`, `api.getConcept(conceptId)`.
- Produces: accessible SVG DAG with layer layout, status legend, side panel, and list fallback.

- [ ] **Step 1: Write the map e2e test**

```ts
test('learning map shows concept status and opens a concept panel', async ({ page }) => {
  await page.goto('/map?chapter=cbse-10-math-real-numbers');
  await expect(page.getByRole('heading', { name: /Learning Map/i })).toBeVisible();
  await page.getByRole('button', { name: /HCF and LCM/i }).click();
  await expect(page.getByRole('dialog')).toContainText(/evidence/i);
});
```

- [ ] **Step 2: Build the map**

Use the API’s `layer` and `order` to place nodes in columns. Draw curved edges with arrow markers. Status is icon + label + colour: secure, developing, gap, early signal, unverified. Click opens a side panel with evidence count, model, prerequisites, resources, “Practise this”, and “Read this”. Provide a keyboard-accessible list view and a legend. On mobile, default to the list.

- [ ] **Step 3: Run build and test**

```powershell
cd frontend
npm run build
npx playwright test e2e/map.spec.ts --project=chromium
```

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/pages/LearningMapPage.tsx frontend/src/pages/LearningMapPage.module.css frontend/src/components/map frontend/e2e/map.spec.ts
git commit -m "feat: add accessible learning map"
```

---

## Task 21: Achievements and Ask Zenith UI

**Files:**
- Create: `frontend/src/pages/AchievementsPage.tsx`, `AchievementsPage.module.css`, `frontend/src/pages/AskZenithPage.tsx`, `AskZenithPage.module.css`
- Create: `frontend/src/components/AskZenith.tsx`, `AskZenith.module.css` (rename `AskSetu`)
- Modify: `frontend/src/App.tsx`, `frontend/src/components/Navigation.tsx`
- Test: `frontend/e2e/achievements.spec.ts`, `ask-zenith.spec.ts`, `ask-zenith-degraded.spec.ts`

**Interfaces:**
- Consumes: `api.getRewards`, `getRewardCalendar`, `getBadges`, `claimDailyReward`, `askTutor`, `getTutorThreads`, `getTutorThread`, `deleteTutorThread`.
- Produces: achievements page and tutor drawer/page with citations and honest degraded state.

- [ ] **Step 1: Build Achievements**

Hero with level ring, XP to next level, coins, current/longest streak. 28-day activity calendar from real study events. Badge grid with earned/locked states, criteria, and progress. Recent reward timeline. No leaderboards, no fake social proof.

- [ ] **Step 2: Build Ask Zenith**

Thread list, new question, suggested prompts from the current chapter, answer with numbered citations, “Sources used” list, quota remaining, delete thread, and offline queue. Render answers as plain text with safe line breaks; no `dangerouslySetInnerHTML`. Show `grounded: false` as “General explanation — not from your library” and `503` as “Tutor unavailable — your question is saved.”

- [ ] **Step 3: Add the degraded-state test**

Intercept `/api/v1/tutor/ask` with a 503 and assert the UI shows the safe message and keeps the question in the outbox. Intercept a 200 with `grounded: false` and assert the label.

- [ ] **Step 4: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/achievements.spec.ts e2e/ask-zenith.spec.ts e2e/ask-zenith-degraded.spec.ts --project=chromium
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/pages/AchievementsPage.tsx frontend/src/pages/AchievementsPage.module.css frontend/src/pages/AskZenithPage.tsx frontend/src/pages/AskZenithPage.module.css frontend/src/components/AskZenith.tsx frontend/src/components/AskZenith.module.css frontend/src/App.tsx frontend/src/components/Navigation.tsx frontend/e2e/achievements.spec.ts frontend/e2e/ask-zenith.spec.ts frontend/e2e/ask-zenith-degraded.spec.ts
git commit -m "feat: add achievements and grounded Ask ZENITH experience"
```

---

## Task 22: Teacher integration and branding sweep

**Files:**
- Modify: `backend/app/services/learner_insights.py`, `backend/app/services/coach_service.py`, `backend/app/services/study_plan.py`, `backend/app/services/smart_check.py`
- Modify: `frontend/src/pages/TeacherDashboardPage.tsx`, `TeacherDashboardPage.module.css`, `frontend/src/components/Navigation.tsx`, `frontend/src/components/OnboardingTour.tsx`, `frontend/src/pages/DoubtQueuePage.tsx`, `frontend/src/pages/NotFoundPage.tsx`, `README.md`
- Test: `backend/tests/test_concept_labels.py`, `frontend/e2e/teacher_evidence.spec.ts`, `branding.spec.ts`

**Interfaces:**
- Consumes: library concepts, teacher evidence matrix.
- Produces: readable concept labels, chapter context in teacher evidence, no user-facing SETU strings.

- [ ] **Step 1: Fix `concept_label`**

Parse scoped IDs after `--`, preserve acronyms (`HCF`, `LCM`, `CBSE`), and title-case small words correctly. Add tests:

```python
def test_scoped_concept_label_is_readable():
    assert concept_label("cbse-10-math--hcf-and-lcm") == "HCF and LCM"

def test_existing_unscoped_label_still_works():
    assert concept_label("concept-photosynthesis") == "Photosynthesis"
```

- [ ] **Step 2: Update teacher evidence**

Show the chapter title and resource kind alongside concept labels. Keep teacher access scoped to their classroom. Do not expose tutor messages or AI chat. Add a test that a teacher sees a library concept label and another classroom’s data is absent.

- [ ] **Step 3: Branding sweep**

Run:

```powershell
Get-ChildItem frontend/src,frontend/index.html,frontend/public,backend/app,README.md -Recurse -File | Select-String -Pattern 'SETU|Setu|setu'
```

Classify every hit: user-facing copy → ZENITH; internal compatibility identifiers (`SetuDeskDB`, `setu_auth_token`, `SETU_*`, `setu-documents`) → keep and document in `docs/OPERATIONS.md`. Rename `AskSetu` to `AskZenith`, `openAskSetu` to `openAskZenith`, and all UI strings. Update Playwright assertions.

- [ ] **Step 4: Run tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_concept_labels.py -q
cd ..\frontend
npm run build
npx playwright test e2e/teacher_evidence.spec.ts e2e/branding.spec.ts --project=chromium
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/learner_insights.py backend/app/services/coach_service.py backend/app/services/study_plan.py backend/app/services/smart_check.py backend/tests/test_concept_labels.py frontend/src/pages/TeacherDashboardPage.tsx frontend/src/pages/TeacherDashboardPage.module.css frontend/src/components frontend/src/pages frontend/e2e README.md docs/OPERATIONS.md
git commit -m "feat: integrate library concepts into teacher evidence and finish rebrand"
```

---

## Task 23: PWA, performance, and accessibility

**Files:**
- Modify: `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/tokens.css`, `frontend/src/App.module.css`, `frontend/src/components/Navigation.module.css`
- Create: `frontend/e2e/accessibility.spec.ts`
- Test: build size, Playwright accessibility.

**Interfaces:**
- Consumes: all pages.
- Produces: updated PWA manifest/icons, route-level code splitting, accessible pages.

- [ ] **Step 1: Update the PWA**

Set manifest `name: "ZENITH — Adaptive learning"`, `short_name: "ZENITH"`, description, theme `#0C6B5F`, background `#F7F4EC`, icons, `display: standalone`, and `orientation: portrait`. Keep `registerType: autoUpdate`. Precache the app shell; do not cache personal API responses.

- [ ] **Step 2: Measure and split the bundle**

Run `npm run build`. Confirm the main entry chunk is ≤ 220 kB gzip. If it is larger, lazy-load the Learning Map, Achievements, Ask Zenith, and Teacher pages; do not add a chart/DAG library. Record sizes in `STATUS_REPORT.md`.

- [ ] **Step 3: Add axe accessibility tests**

Install `@axe-core/playwright` as a dev dependency. Add tests for Home, Explore, Chapter, Practice, Map, Achievements, and Profile:

```ts
const results = await new AxeBuilder({ page }).analyze();
expect(results.violations.filter(v => ['serious', 'critical'].includes(v.impact!))).toEqual([]);
```

- [ ] **Step 4: Manual accessibility checks**

Keyboard-only navigation, focus order, skip link, 44px targets, reduced motion, high contrast, 360px width, and screen-reader labels for the map and progress rings. Record results.

- [ ] **Step 5: Run build and tests**

```powershell
cd frontend
npm run build
npx playwright test e2e/accessibility.spec.ts --project=chromium
npx playwright test --project=mobile
```

- [ ] **Step 6: Commit**

```powershell
git add frontend/vite.config.ts frontend/index.html frontend/src/tokens.css frontend/src/App.module.css frontend/src/components/Navigation.module.css frontend/package.json frontend/package-lock.json frontend/e2e/accessibility.spec.ts
git commit -m "perf: finalize PWA, code splitting, and accessibility"
```

---

## Task 24: Deployment configuration and documentation

**Files:**
- Create: `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/.env.production.example`, `render.yaml`, `frontend/.env.production.example`, `frontend/public/_redirects`, `frontend/public/_headers`, `scripts/smoke_production.ps1`
- Modify: `README.md`, `docs/OPERATIONS.md`, `STATUS_REPORT.md`
- Create: `docs/CONTENT_AUTHORING.md`, `docs/DEPLOYMENT.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: reproducible local production build and deployment configs; no claim of live deployment.

- [ ] **Step 1: Pin backend dependencies**

Generate `requirements.txt` from the working `.venv` with exact versions for runtime packages. Add `requirements-dev.txt` with pytest, pytest-asyncio, sympy, ruff. Verify a clean install in a fresh venv or Docker build.

- [ ] **Step 2: Add the Dockerfile and Render config**

Dockerfile: Python 3.12-slim, `tesseract-ocr`, non-root user, `pip install -r requirements.txt`, copy app, `CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]`. `render.yaml` declares the Docker web service, health check `/api/v1/health`, and `sync: false` env vars. `FRONTEND_ORIGINS` is explicit.

- [ ] **Step 3: Add frontend hosting configs**

`_redirects`: `/* /index.html 200`. `_headers`: CSP allowing self, Google Fonts, and the API origin; HSTS; `X-Content-Type-Options: nosniff`; `Referrer-Policy: strict-origin-when-cross-origin`; `Permissions-Policy: camera=(), microphone=(), geolocation=()`. Document Cloudflare Pages and Render static settings.

- [ ] **Step 4: Write the smoke script**

`scripts/smoke_production.ps1` takes `-ApiBase` and `-WebBase`, checks `/api/v1/health`, `/api/v1/library/catalogue`, one chapter, one resource (with a test token if provided), CORS preflight, and the frontend title. It must not print tokens.

- [ ] **Step 5: Build and run locally**

```powershell
cd backend
docker build -t zenith-api .
docker run --rm -p 8002:8000 --env-file .env zenith-api
```

Use a disposable database or a read-only check; do not point the container at production for destructive tests. Run `npm run build` and `npm run preview`, then run the smoke script against `http://127.0.0.1:8002` and `http://127.0.0.1:5173`.

- [ ] **Step 6: Write docs**

`README.md`: product overview, architecture, local setup, test commands, content pipeline, deployment, limitations. `docs/CONTENT_AUTHORING.md`: how to add a chapter/resource, schema rules, validation, publication, rollback. `docs/DEPLOYMENT.md`: Render/Cloudflare steps, env vars, migration, smoke. `docs/OPERATIONS.md`: RLS posture, backups, AI provider, quotas, incident runbook. `STATUS_REPORT.md`: exact commands/results, blockers, next steps.

- [ ] **Step 7: Commit**

```powershell
git add backend/requirements.txt backend/requirements-dev.txt backend/Dockerfile backend/.dockerignore backend/.env.production.example render.yaml frontend/.env.production.example frontend/public/_redirects frontend/public/_headers scripts/smoke_production.ps1 README.md docs STATUS_REPORT.md
git commit -m "chore: add production packaging, deployment configs, and docs"
```

---

## Task 25: Full verification and final review

**Files:**
- Modify: `STATUS_REPORT.md` only (plus fixes found by review)
- Test: all backend, all Playwright, build, smoke.

**Interfaces:**
- Consumes: every prior task.
- Produces: verified evidence; no unverified completion claims.

- [ ] **Step 1: Run the complete backend suite**

```powershell
docker compose -f backend/docker-compose.test.yml up -d --wait
$env:SETU_TEST_DATABASE_URL='postgresql://setu:setu_test@127.0.0.1:55432/setu_test'
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass; record counts.

- [ ] **Step 2: Run the content pipeline from scratch**

On the disposable test database, run migrations, seed, validate, and verify counts:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_library --publish
.\.venv\Scripts\python.exe -m scripts.validate_library --root app/content/library
.\.venv\Scripts\python.exe -m scripts.verify_library_math
```

Expected: 4 chapters, 20 visible resources, 4 hidden diagnostic banks, ≥60 questions, no validation errors.

- [ ] **Step 3: Run the frontend build and all Playwright tests**

```powershell
cd frontend
npm run build
npx playwright test
```

Expected: build passes; desktop and mobile suites pass. Record any flaky tests and rerun.

- [ ] **Step 4: Run the local production smoke**

Start the backend and `npm run preview`, then:

```powershell
powershell -File scripts/smoke_production.ps1 -ApiBase http://127.0.0.1:8001 -WebBase http://127.0.0.1:5173
```

Expected: health ok/degraded with a safe reason, catalogue 4 chapters, chapter 5 resources, frontend title ZENITH.

- [ ] **Step 5: Security and secret audit**

```powershell
git grep -n -E "service_role|SUPABASE_SECRET_KEY|GROQ_API_KEY|Bearer [A-Za-z0-9]" -- . ':!*.example' ':!docs/**'
```

Confirm no secret is committed. Confirm no service-role key is in the frontend bundle. Confirm `/health`, `/tutor`, and error responses do not echo keys.

- [ ] **Step 6: Fresh reviewer pass**

Spawn a fresh `general` subagent with the spec, plan, and diff. Ask it to check: spec coverage, authorization, idempotency, no fabricated data, no user-facing SETU, no broken existing flows, and test evidence. Fix every blocking finding and rerun the affected tests.

- [ ] **Step 7: Update STATUS_REPORT and commit**

Record exact commands, pass/fail counts, bundle sizes, known limitations (content is machine-validated and self-reviewed; independent teacher review recommended; live deployment pending credentials). Commit:

```powershell
git add STATUS_REPORT.md
git commit -m "docs: record ZENITH verification evidence and known limitations"
```

---

## Self-Review Notes

- **Spec coverage:** branding (Task 2, 22), library data model/content (Tasks 4–10), APIs/access (Task 11), BKT/prerequisites (Task 12), rewards (Task 13), diagnostics/practice (Task 14), AI (Task 15), onboarding/profile (Task 16), Home/Explore/Chapter (Task 17), reader/offline (Task 18), Practice UI (Task 19), Map (Task 20), Achievements/Ask (Task 21), teacher (Task 22), PWA/a11y (Task 23), deployment/docs (Task 24), verification (Task 25).
- **Type consistency:** `ValidationReport`, `SeedResult`, `MasteryResult`, `RewardAward`, `LibraryBundle`, `recommend_next`, `select_practice_questions`, and API field names are used consistently across tasks.
- **Review Focus tests:** each of the five failure modes has a named test in an owning task.
- **Cut line:** extra chapters/subjects, voice/image doubts, parent accounts, and leaderboards. The core loop, library quality, and honest evidence are not cut.

## Execution Handoff

Recommended: **Native** execution in this session, then one fresh reviewer on the whole branch. The tasks share interfaces (access policy, mastery result, rewards hook, API types) and the deadline is tight; a subagent per task would spend more time re-reading shared context than building. If the user prefers maximum independence, use subagent-driven execution with the same task order.
