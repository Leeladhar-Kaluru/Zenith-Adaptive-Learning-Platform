# ZENITH — Transformation Assessment (planning only, no code changed)

**Date:** 2026-11-10 · **Repo:** `C:\projects\setu - V2` (branch `master`, remote `Leeladhar-Kaluru/SETU-Adaptive-Learning-Platform`)
**Status:** Proposal awaiting approval. No implementation, deletion, migration or cloud change has been made.

Legend used throughout: **[EXISTS]** verified in code/DB · **[PARTIAL]** exists but incomplete/incorrect · **[PROPOSED]** new · **[EXPERIMENTAL]** ship behind a flag, measure first · **[MISSING]** required, absent.

---

## 0. What I actually inspected (and what I could not)

| Inspected | How |
|---|---|
| Problem statement (all 4 pages) | Read the PDF in full |
| Repository | `git status`, every backend module/route/model, migrations 001–009, content JSON, frontend routes/pages/package.json, render.yaml, vercel.json, Dockerfile, requirements.txt, prior spec `docs/superpowers/specs/2026-11-06-zenith-rebuild.md` (outline + §6, §9 in detail) |
| Live Supabase project `Setu` (`mevbffduofdpalzimfye`, ap-south-1) | Read-only SQL: Alembic head, table row counts, buckets, roles; security advisors |
| Frontend build | `npm run build` → **passes** (4.4 s). Main chunk 453 kB (141 kB gzip), KaTeX 264 kB, PWA precache 1.34 MB / 84 entries |
| Canvas Classes | 12 public pages fetched (homepage, `/class-11`, one full Live Book lesson, flashcards index + a deck, handwritten notes, interactive periodic table, salt analysis lab, question-bank index; Crucible, Study Planner, Assertion-Reason and Login only rendered shells) |

| Not inspected | Why |
|---|---|
| Backend test suite | `pytest` refuses to run without `SETU_TEST_DATABASE_URL` (disposable Docker Postgres from `backend/docker-compose.test.yml`). **Not run — no pass/fail claim.** |
| Running UI in a browser | Not started this session (would connect to the live DB). No visual claims below. |
| Vercel projects | Vercel API returned 403 for scope `leeladhar2804-2489s-projects` (team access not authorised for this connector). |
| Render / Groq / Backblaze dashboards | No access. Groq model availability and rate limits **unverified**. |
| Canvas Classes logged-in features | Crucible, Study Planner, progress tracking are client-rendered/login-gated. |

---

## 1. The actual problem

The brief (Code Kernel '26, with Canvas Classes) is narrower and sharper than "AI education app":

1. **One pace fails.** Same lesson, same questions, same pace → fast learners wait, struggling learners build on gaps, and *nobody can see* who understood what.
2. **Gaps surface too late.** End-of-chapter tests find gaps after the class has moved on. The product must detect gaps *during* learning.
3. **Gaps are cumulative and cross-grade.** "A basic missed in Class 6 or 7 makes topics built on it harder later." This is the explicit justification for a prerequisite graph spanning grades.
4. **Indian constraints are requirements:** boards/syllabi, large classes, home language ≠ medium of instruction, shared phones, limited data, tuition overload, board-exam pressure in Class 10.
5. **Adapt Learn, Solve *and* Test** — "what comes next, how, and how fast."
6. **Teacher at the centre.** Guiding question: *how does this empower the school teacher?*
7. The brief's five key questions are effectively our acceptance criteria: How do you know what a student understood? How do you adapt when they struggle *or move ahead*? How does it work in a typical Indian school? How does it help, not replace, the teacher? Who uses it and how often?

Note: the hackathon rounds (Decode 21–24 Oct, Build 25–29 Oct, Prove 30–31 Oct) are over. This plan targets a real deployable product, not the round deliverable.

**My interpretation of the usage model** (needs your confirmation, see §14): a teacher runs a classroom; students use ZENITH 3–5 times a week for 15–25 minutes on a phone (often shared), at school or home; the teacher checks the class view weekly and before teaching a chapter. Independent learners can use it without a classroom.

---

## 2. Canvas Classes — what to adopt, improve, avoid

**Verified in fetched HTML (working content):**
- Hierarchy **Class → Subject → Chapter → numbered sections** (e.g. 4.1–4.11), each chapter showing page count and per-chapter progress ("0/17, Not started").
- A full lesson page structured as: hook ("Did You Know") → numbered steps with bold key terms → table → captioned image → "When it goes wrong" → real-life examples → a commit-before-reveal MCQ → "Remember" summary → "Check your understanding (3 quick questions)" → Previous/Next. Sidebar tags lessons as Quiz/Reasoning; header links to Review and Teach modes.
- Flashcards grouped by chapter topics with counts; cross-links chapter ↔ notes ↔ flashcards ↔ questions.
- Reference tools with real data (periodic table, oxide nature table, salt-analysis lab tables with Apprentice/Analyst/Exam tracks).

**Advertised only (could not verify):** simulations "you can change", quiz that remembers where you slipped, spaced-repetition flashcards/mastery levels, study-planner tracking, Hinglish mode, Teach-for-my-class mode.

**Defects observed:** quiz answers marked correct in static HTML (answer leakage); a flashcard showing a rendering artifact; inconsistent claimed PYQ counts.

| Adopt | Improve for Classes 6–10 | Avoid |
|---|---|---|
| Short numbered sections, one idea each | Shorter sections (≤150 words), larger type, more visuals per idea | Video-first content, JEE/NEET framing, PYQ-count marketing |
| Commit-then-reveal checks inside the lesson | Make every check **evidence** for the learner model (Canvas's are display-only as far as I could see) | Answer keys in client HTML — ours stay server-side until submission |
| "When it goes wrong" / trap callouts | Turn each into a **tagged misconception** that distractors map to | Inflated counts, "coming soon" tiles that look like content |
| Cross-linked chapter resources | Link to **prerequisite** chapters across grades, not just sibling resources | A separate disconnected "tools" universe |
| Review mode / Teach mode | Teach mode = teacher projects a lesson and sees live class check results | |

---

## 3. Audit of the current repository

### 3.1 Two products in one tree

The working tree contains **(a)** the committed SETU document-upload→RAG→generated-lesson product (migrations 001–008, live in Supabase), and **(b)** a large **uncommitted** ZENITH rebuild started 2026-11-06 (migration 009, library/BKT/practice/rewards/tutor/diagnostics services, 56 content JSON files, new pages and UI kit, Dockerfile, render.yaml, vercel.json). `git status` shows ~45 modified tracked files and ~90 untracked files. **None of the ZENITH work is committed; a disk failure or a bad `git checkout` loses it.**

### 3.2 Naming conflict (blocking decision)
`AGENTS.md` rule 1 says the visible product name is **SETU, everywhere**. `STATUS_REPORT.md`, `render.yaml`, `config.APP_NAME`, new pages and logos say **ZENITH**. `main.py` still returns `"product": "SETU"`; `tutor_service.py` says "Product name is strictly SETU"; the repo and the Supabase bucket are `setu-*`. You now call it ZENITH. AGENTS.md rule 1 must be updated by you (I won't silently override a project rule).

### 3.3 Backend (FastAPI, SQLAlchemy 2, Alembic, psycopg3) — verified
| Area | Files | State |
|---|---|---|
| Auth | `core/security.py` | **[EXISTS]** Verifies Supabase JWT via Supabase Auth API with caching; `X-User-Id` test header only when `APP_ENV=test` *and* `SETU_TEST_AUTH=true`. Roles from `user_profiles.role` (student/teacher/admin). Sound. |
| AI provider | `core/ai_provider.py` | **[EXISTS]** OpenAI-compatible client, 429 `Retry-After` backoff, fallback model on 404/429/5xx. Reusable. Local `.env` has `ENABLE_REMOTE_AI=false` → **AI is currently off locally**. No LM Studio base URL configured. Fallback model `qwen/qwen3.8-27b` is **unverified** against Groq's model list. |
| Document pipeline | `api/v1/documents.py`, `services/{ingestion,extraction,chunking,retrieval,lesson_generator(1,984 lines),pipeline_runner,generation_queue}.py`, `worker.py`, `core/storage.py`, `backend/tessdata/` | **[EXISTS] → remove** (§6). `main.py` starts the pipeline loop inside the API process. |
| Old mastery | `services/{adaptive_engine,attempt_service,learner_insights,coach_service,study_plan,smart_check}.py` on `concept_evidence`/`concept_mastery_snapshots` | **[PARTIAL]** rule-based bands; tied to document-generated `learning_paths`. |
| New library | `services/library_{service,seed,validator,retrieval,access}.py`, `api/v1/library.py`, `models/library.py`, content JSON | **[PARTIAL]** see 3.5 |
| New BKT | `services/bkt.py`, `models/mastery.py` | **[PARTIAL]** see §9.1 |
| Teacher | `api/v1/teacher.py` (611 lines), `classroom.py` | **[EXISTS]** but reads the *old* `concept_evidence` tables. |
| Rewards | `services/rewards_service.py`, `api/v1/rewards.py` | **[EXISTS, uncommitted]** XP/coins/badges/streaks. |

**Critical defect — two disconnected learner models.** New practice writes `bkt_states`/`bkt_events`; the teacher dashboard, coach, study plan and profile read `concept_evidence`/`concept_mastery_snapshots`. A student practising in the new Library would be **invisible to the teacher.**

**Security defect — drafts are readable.** `library_access.can_read_library_path` returns `True` for `library_status in ("published","active","draft","ready")` **or `None`**. Unpublished/unreviewed content is served to students.

**Runtime reads bypass the database.** `library_retrieval.py` (tutor grounding) reads JSON from disk and is hard-wired to `content/library/cbse-10-math` → the tutor is only grounded for Class 10 Maths. `practice_service._load_questions_from_content_dir` also reads disk. Publication state, versioning and review are therefore not enforced at runtime.

### 3.4 Live database (Supabase `Setu`) — verified read-only
- **Alembic head = `008`. Migration 009 has never been applied to production.** This is good news: the 009 design can be replaced freely.
- 27 public tables. Rows: `documents 2`, `document_pages 344`, `document_chunks 444`, `learning_paths 6`, `path_lessons 66`, `lesson_versions 66`, `questions 528`, `quiz_attempts 17`, `study_events 17`, `concept_evidence 17`, `classrooms 10`, `classroom_memberships 10`, `user_profiles 8` (6 student, 2 teacher), `auth.users 8`; `resources`, `resource_sources`, `resource_rights`, `generation_jobs`, `sync_events` empty.
- Storage: one private bucket `setu-documents`, 5 objects.
- Extensions `vector`, `pg_trgm` in `public`.
- **Advisors:** RLS enabled with no policies on all 27 tables (acceptable *deny-all* posture since only the backend touches data via direct connection — keep it, document it); `public.rls_auto_enable()` is `SECURITY DEFINER` and **executable by `anon` and `authenticated` via `/rest/v1/rpc`** (fix); leaked-password protection disabled (enable); extensions in `public` (move when dropping pgvector).
- A second project `Swiftradish` exists and is `INACTIVE` — unrelated, untouched.

### 3.5 Content library (uncommitted JSON)
6 curricula, 10 chapters: Class 6 Integers, Class 7 Algebraic Expressions, Class 8 Linear Equations, Class 9 Number Systems, Class 10 Maths × 4, Class 10 Science × 1. Assessment of a sampled lesson (`cbse-07-math/algebraic-expressions-01-introduction.json`):
- Plain-text maths (`4x^2 - 7xy`), not proper notation.
- **One** practice question; `checkpointTest: []`; no diagram; no misconception tags.
- `validation.status: "ready"` is **self-declared inside the file**, with a check named `cbse_alignment` citing "CBSE Class 7 Chapter 12". **Classes 6–8 NCERT textbooks were replaced** (Ganita Prakash / Curiosity, NCF-SE 2023, rolled out 2024-25 and 2025-26), so old chapter numbers are likely wrong for 6–8. Every mapping needs a curriculum *version* and human verification.
- STATUS_REPORT claims (198/198 SymPy, 225/225 DAG checks) refer to scripts I did not re-run; they verify arithmetic/acyclicity, not pedagogy or curriculum alignment.

**Verdict:** the content is a useful *seed* for concept IDs and prerequisite edges, not publishable chapters.

### 3.6 Frontend (React 19, Vite 6, TS, CSS Modules, Dexie, KaTeX, vite-plugin-pwa, lucide-react)
- Matches AGENTS.md rule 4. No Tailwind/shadcn. Builds cleanly.
- Routes: `/`, `/explore`, `/chapter/:slug`, `/learn/:lessonId`, `/lesson/:lessonId`, `/practice`, `/map`, `/achievements`, `/ask`, `/sources`, offline, doubts, student/teacher dashboards. Duplicated lesson routes; `/sources` and home's `AddSourcePanel`/`PlanReviewDialog` belong to the document product.
- Reusable: `components/ui/*` (Button, Card, Badge, Callout, Input, Progress, MathText), `components/layout/*`, `components/visuals/*` (NumberLine, FractionModel, CoordinateGrid, ConceptMap, ProcessDiagram, VisualRenderer), `db/indexedDB.ts`, `services/syncManager.ts`, `AuthContext`.
- `api.ts` (1,000+ lines) mixes both products.
- Bundle: 141 kB gzip main chunk is acceptable but should drop with document code removed; KaTeX should load only on lessons that use maths.

### 3.7 Deployment config
- `render.yaml` deploys **branch `main`**; the repo uses **`master`** → auto-deploy would never fire.
- `entrypoint.sh` runs `alembic upgrade head` on every boot — fine for one instance, unsafe if scaled; needs an advisory lock or a separate release step.
- `EMBEDDED_PIPELINE=true` and `STORAGE_BUCKET_DOCUMENTS` in render.yaml — obsolete after removal.
- Backend `.env` contains `SETU_DEMO_TEACHER_BYPASS`, which no code reads — delete the variable.
- **Backblaze B2: no code references it.** It's not part of the running system.

---

## 4. Reuse

Supabase Auth + JWT verification; role model; classroom/membership models and teacher APIs (re-pointed at the new evidence); FastAPI/SQLAlchemy/Alembic skeleton; `ai_provider.py`; Dexie + sync manager pattern (idempotency keys); UI kit, layout, visual components; KaTeX `MathText`; PWA setup; Dockerfile (trimmed); vercel.json; concept IDs/prerequisite edges and the better worked examples from the JSON seed; rewards service (simplified, §10).

## 5. Rebuild

1. **Content model** — DB-native, versioned, with review/publish states; frontend and tutor read only *published* rows (replaces filesystem reads and the `learning_paths.is_library` overload in 009).
2. **Learner model** — one immutable evidence log → BKT concept state + Elo item/learner ratings; retire `concept_evidence`/snapshots and the rule engine after migration.
3. **Teacher dashboard** — on the new evidence; evidence-cited recommendations; assignments; reassessment tracking.
4. **Tutor grounding** — Postgres full-text search over published lesson blocks for the student's current board/grade/lesson (no embeddings needed at this scale).
5. **Lesson reader** — block renderer for typed blocks (text, figure, worked example, check, activity, misconception callout, summary) with variants.
6. **`api.ts`** — split per domain; remove document types.
7. **Migration 009** — rewrite before it ever reaches production.

## 6. Remove (after reference checks, in one reviewed PR)

**Backend code:** `api/v1/documents.py`, `services/{ingestion,extraction,chunking,retrieval,lesson_generator,pipeline_runner,generation_queue}.py`, `worker.py`, document parts of `core/storage.py`, `models/{documents,jobs}.py`, `backend/tessdata/`, scripts `ingest_first_flight.py`, `run_m3_first_flight_pipeline.py`, `run_m4_verification.py`, `verify_m4_e2e_journeys.py`, `dump_questions.py`, `ensure_all_students_have_paths.py`, and tests that only cover these. `sync_service.py` imports `retrieval_service` — refactor the offline-doubt sync to the new tutor before deletion. `learning_paths.py` and `documents.py` import `lesson_generator` — remove with them.
**Config/deps:** `pymupdf`, `python-docx`, `python-pptx`, `pgvector`, `EMBEDDING_*`, `MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_EXTENSIONS`, `STORAGE_BUCKET_DOCUMENTS`, `EMBEDDED_PIPELINE`, `SETU_DEMO_TEACHER_BYPASS`.
**Frontend:** `pages/SourcesPage*`, `pages/home/{AddSourcePanel,PlanReviewDialog,StudyRecordPanel}*`, upload/ingestion API + types, document statuses in `DynamicActivityIndicator`, duplicate `/lesson/:id` route.
**Repo clutter:** `scratch/`, `test.db`, `test-results/`, `frontend/tsconfig.tsbuildinfo` (should be ignored), stale audit/acceptance JSON in `context/` (archive, don't delete history), `agents/teamwork/`.
**Database (separate, approval required — §8.4):** `documents`, `document_pages`, `document_chunks`, `generation_jobs`, `resources`, `resource_sources`, `resource_rights`, then `vector` extension; bucket `setu-documents` (5 objects).

**Keep:** git history (no rewrites), `.env` files, `auth.*`, `storage` schema, user accounts.

---

## 7. Target architecture

```
Browser PWA (React 19/Vite, Cloudflare Pages or Vercel)
  │  Supabase Auth (JWT) directly for sign-in only
  │  everything else → HTTPS JSON
  ▼
FastAPI modular monolith (one container)
  ├─ content      read published curriculum; admin import/review/publish
  ├─ learning     evidence ingest, answer verification (deterministic)
  ├─ model        BKT + Elo updates (pure functions, versioned params)
  ├─ policy       next-best-action, item selection, prerequisite investigation
  ├─ teacher      class aggregates, recommendations, assignments
  ├─ tutor        AI explanations/hints/doubts (provider abstraction)
  ├─ sync         idempotent offline batch ingest
  └─ jobs         small Postgres-queue for AI drafts/translations (no worker process needed at v1)
  ▼
Supabase Postgres (single source of truth, RLS deny-all, backend-only access)
Static content media (SVG/WebP) bundled with frontend or public Supabase bucket via CDN
Groq (prod) / LM Studio (local) behind ai_provider
```

Principles: no microservices; deterministic layers (verification, model, policy) are pure Python with unit tests and no LLM; the LLM only *generates teaching text* and never writes scores or mastery. Voice later = a new `speech` adapter beside `ai_provider`; the tutor API already takes text in/out, so ASR/TTS bolt on at the edge.

---

## 8. Database and content model

### 8.1 Curriculum & content [PROPOSED]
```
boards(id, code, name)                                   -- CBSE, TS-SSC …
curriculum_versions(id, board_id, label, effective_year, source_note)   -- "NCERT 2025-26 (Ganita Prakash)"
subjects(id, code, name)
chapters(id, curriculum_version_id, grade, subject_id, number, title, slug,
         status: listed|in_production|published|retired)     -- listed = "Coming soon"
topics(id, chapter_id, order, title)
concepts(id, slug, title, subject_id, grade_level, description)  -- board-agnostic
chapter_concepts(chapter_id, concept_id, role: core|foundation)
concept_edges(prereq_concept_id, concept_id, strength 0..1, rationale)  -- DAG, validated
lessons(id, chapter_id, topic_id, order, slug)
lesson_versions(id, lesson_id, version, language, status: draft|in_review|changes_requested|approved|published|retired,
                objectives[], blocks jsonb (schema-validated), estimated_minutes,
                origin: human|ai_assisted, author_id, reviewer_id, reviewed_at, published_at, content_hash)
items(id, kind: mcq|multi|numeric|expression|order|match|short, stem, payload jsonb, answer_spec jsonb (server-only),
      difficulty_prior, purpose: check|practice|test|probe, origin, status, version)
item_concepts(item_id, concept_id, weight)
misconceptions(id, concept_id, code, description, remediation_lesson_id)
item_option_misconceptions(item_id, option_key, misconception_id)
activities(id, kind, spec jsonb)                      -- typed interactive widgets: number-line drag, fraction builder, balance model…
media_assets(id, path, kind, alt_text, author, licence: original|cc-by|…, attribution, rights_verified_by)
lesson_links(lesson_id, related_lesson_id, kind: prerequisite|enrichment|revision)
content_audit(id, entity, entity_id, action, actor_id, at, diff)
```
Lesson block kinds: `hook`, `explain`, `figure`, `worked_example` (steps + "why this step"), `check` (→ item id), `activity`, `misconception`, `real_life`, `summary`, each with optional `variant: core|simpler|visual|challenge`.

### 8.2 Learner, classroom, adaptive [PROPOSED]
```
user_profiles(id=auth.uid, role, display_name, grade, board_id, curriculum_version_id,
              preferred_language, ui_language, age_band, consent_status)    -- no DOB, no phone, no school ID
guardian_consents(id, student_id, method, consented_at, withdrawn_at, scope)
classrooms(id, teacher_id, name, grade, subject_id, curriculum_version_id, join_code)
classroom_memberships(classroom_id, student_id, joined_at, status)
evidence_events(id, student_id, item_id, item_version, concept_ids[], context: learn_check|solve|test|probe|review,
                response jsonb, correct, partial_score, hints_used, attempts_on_item, duration_ms,
                misconception_id, client_event_id UNIQUE, occurred_at, received_at)     -- append-only
concept_states(student_id, concept_id, p_known, n_obs, n_correct, last_obs_at,
               status: unassessed|learning|secure|gap_suspected|gap_confirmed, param_version)
learner_ratings(student_id, subject_id, theta, n)          -- Elo ability
item_ratings(item_id, beta, n)                             -- Elo difficulty
recommendations(id, student_id, action, concept_id, lesson_id, reason jsonb (evidence ids), model_version, created_at, outcome)
interventions(id, student_id, concept_id, kind, started_at, pre_p, post_p, closed_at)
assignments(id, classroom_id, lesson_id|item_set, due_at, created_by)
tutor_threads / tutor_messages(… retention 90 days, no PII in prompts)
rewards (simplified), sync_batches(id, client_batch_id UNIQUE, …)
```

### 8.3 Content workflow [PROPOSED]
Content-as-code: chapters authored as JSON/YAML + SVG in `content/` → CI runs schema validation, SymPy answer checks, DAG acyclicity, KaTeX parse, image alt-text/licence checks → `zenith-content import` loads as `draft` (idempotent by content hash) → reviewer opens an in-app **Review** screen (role `reviewer`), reads the lesson exactly as a student sees it, approves or requests changes → admin publishes. AI-assisted drafts carry `origin=ai_assisted` and cannot skip review; the DB enforces `published ⇒ reviewer_id IS NOT NULL`. Students' APIs filter `status='published'` at the query layer, and a test asserts no draft is reachable.

### 8.4 Data migration & cleanup sequence
1. Create a branch/tag of the current tree (needs your OK to commit).
2. `pg_dump` (data + schema) of the `Setu` project and SHA-256 archive of the 5 storage objects to an offline location; record in `context/RESET_REPORT.md`.
3. New migrations `009_content_core`, `010_learner_model`, `011_teacher`, replacing the unapplied 009.
4. Re-point classrooms/memberships/profiles (kept). Old `quiz_attempts`/`concept_evidence` (17 rows each, test accounts?) are **not** converted — archived only.
5. App code stops referencing legacy tables; one release later, migration `0xx_drop_document_legacy` drops them, after your explicit approval and a fresh backup. Bucket deletion is a separate, approved step.

---

## 9. Adaptive learning and probabilistic modelling

### 9.1 What exists vs what's needed
`bkt.py` is a correct textbook BKT update, but: (a) guess/slip are per-concept constants; a 4-option MCQ has a guess floor near 0.25 while a numeric answer is near 0; (b) the hint "penalty" (`posterior − 0.15`) is not Bayesian; (c) "2 consecutive failures ⇒ gap" ignores what the prerequisites show; (d) the band label `not_started` is assigned to students who *have* attempted and are struggling; (e) it diverges from the existing spec's own design (difficulty-adjusted guess/slip, hint blending, shadow mode); (f) no uncertainty shown; (g) parameters are guesses presented as if fitted.

### 9.2 Proposed model stack (each tied to a decision)

| Layer | Model | Decision it serves |
|---|---|---|
| Evidence | Append-only `evidence_events` | Audit; re-fit later; teacher drill-down |
| Verification | Deterministic: option key, numeric tolerance, SymPy equivalence for expressions | Correctness. Never the LLM |
| Concept knowledge | **BKT per concept**, item-type-specific guess (`mcq4 0.25`, `mcq3 0.33`, `numeric/expression 0.05`) and slip by difficulty; *assisted* observations (hint used) update with high guess (≈0.6) so they count as weak evidence; multi-concept items update each concept, weighted by `item_concepts.weight` | Is concept secure? Move on? |
| Uncertainty | Evidence count + recency; status `unassessed` until n ≥ 3 | Prevents "mastered" from one lucky answer; teacher sees confidence |
| Item difficulty / ability | **Elo (online Rasch)**: `P(correct)=σ(θ−β)`, updates with decaying K | Choose next item at ~70–80% expected success; harder items for fast learners; calibrates item difficulty from real data |
| Prerequisite investigation | DAG traversal + targeted probes (below) | Revisit basics vs practise more |
| Policy | Explainable rule table over the above | Next best action |
| Retention | Leitner-style review intervals for secure concepts (1, 3, 7, 21 days) | Revision prompts before board exams |

**Why not full IRT now:** 2PL/3PL needs hundreds of responses per item to calibrate; we have none. Elo gives Rasch-like estimates online and converges as data accumulates; we can fit IRT offline later from `evidence_events`. **Why not DKT/neural models:** no data, not explainable to teachers.

**Parameter honesty:** v1 BKT params are expert priors stored with `param_version='prior-v1'`. Once a concept has ~500+ observations, fit with EM (pyBKT) offline, compare log-loss/Brier on held-out students, and only then promote. The UI never shows raw probabilities to students; teachers see bands + evidence counts.

### 9.3 Prerequisite gap investigation
Triggered when concept `c` is `p_known < 0.4` after ≥ 3 observations, or 2 errors share a misconception that maps to a prerequisite:
1. Collect ancestors of `c` up to depth 3, ordered by edge strength × (1 − p_known) × (uncertainty bonus if unassessed).
2. For the top 1–2 unassessed/uncertain ancestors, give a **2-item probe** (`purpose=probe`).
3. Mark `gap_confirmed` on the *deepest* ancestor that fails while its own prerequisites are secure; otherwise `c` itself needs practice.
4. Intervention: assign the prerequisite's `simpler`/`visual` lesson variant + guided practice → reassess (2–3 items) → return to `c`. Record pre/post `p_known` in `interventions` → this is the "improvement after targeted intervention" metric for teachers.

### 9.4 Same model across Learn / Solve / Test
- **Learn:** in-lesson checks are evidence (`learn_check`, lower weight). A failed check swaps the next block to its `simpler` or `visual` variant; a strong prior lets a fast learner skip to the summary + challenge block. Concepts with a confirmed prerequisite gap show a "Strengthen this first" link before the lesson.
- **Solve:** guided practice uses Elo to pick items near 75% success, hints stepwise (scaffold → worked step → full solution); misconception-tagged wrong answers trigger targeted feedback.
- **Test:** chapter tests use a blueprint (concept × difficulty coverage); results update BKT with full weight; post-intervention reassessments are short adaptive tests.

### 9.5 Next-best-action rules (deterministic, explained)
`gap_confirmed in prereq` → revisit prerequisite · `unassessed` → short probe or start lesson · `learning, n<5` → guided practice · repeated misconception → simpler explanation / extra visual · `secure, θ high, fast pace` → challenge items, enrichment, unlock next concept early · `secure, due for review` → revision · after intervention → reassessment. Every recommendation stores the evidence IDs behind it and renders a plain-language reason.

### 9.6 Fast learners
Evidence-based acceleration: if the first 3 probe/check items on a concept are correct with no hints at above-median difficulty, mark the concept `secure` provisionally, offer "Skip ahead" and challenge items; one later error reverts acceleration on that concept only.

---

## 10. UI/UX transformation

**Student IA (mobile-first, bottom nav):** *Today* (one clear next step + reason, assigned work, review due) · *Learn* (Board → Class → Subject → Chapter → Lesson; class/board preselected from profile; "Coming soon" chapters visibly marked, never padded) · *Practice* (adaptive Solve + chapter Tests) · *Map* (concept map for the chapter with prerequisite paths, statuses with confidence) · *Ask* (tutor scoped to current lesson).
**Lesson reader:** one section per screen on phones, progress dots, sticky "Check" moments, worked examples with step reveal, figures as SVG with alt text, KaTeX math, language toggle for explanations ("AI-translated" label until reviewed), save-for-offline.
**Teacher:** *Class* (who needs help this week, ranked by evidence), *Concepts* (heatmap students × concepts with evidence counts), *Misconceptions* (grouped, with suggested prerequisite lesson), *Student* (timeline, interventions and their effect), *Assign* (lesson / practice / reassessment), *Teach mode* (project a lesson; students answer checks live).
**Design system:** keep "The Learning Desk" tokens and CSS Modules; one accent colour + semantic status colours; 16px+ body, 44px targets; no decorative stats, no gradients, no fake activity, empty states that say what to do next. Gamification trimmed to streak + chapter completion + a few badges — no leaderboards (exam-pressure context) and no coins.
**Process:** Stitch MCP is not available in this environment (also noted in prior STATUS_REPORT). I'll design in code against the token system and verify with browser screenshots at 360/768/1280 unless you enable Stitch.

---

## 11. Deployment strategy

| Component | Free option | Limits that matter | Paid when real students use it |
|---|---|---|---|
| Frontend | **Cloudflare Pages** (free, commercial use allowed) or Vercel Hobby (non-commercial use only) | Both fine for static PWA | $0 (CF) / Vercel Pro $20/mo if commercial |
| API | **Render free** web service (Docker) | Spins down after ~15 min idle; cold start often ~30–60 s; 512 MB RAM; 750 instance-hours/month; no SLA | Render Starter ~$7/mo (always on) |
| Alternative API | Google Cloud Run (free tier, scales to zero, cold start ~2–5 s) | Needs a billing account | Pennies at pilot scale |
| DB/Auth | **Supabase free** (current) | Project **pauses after 7 days inactivity**; 500 MB DB; 1 GB storage; no automated backups | Supabase Pro $25/mo (backups, no pausing) — I consider this unavoidable for real student data |
| AI | Groq free tier | Per-model RPM/RPD/TPM caps (verify in console); free tier may be fully consumed by one class | Groq pay-as-you-go (cheap at this scale) |
| Media | Bundled SVGs via CDN; Supabase public bucket for larger images | 1 GB free | — B2 not needed for v1 |

**When Render free sleeps:** the PWA shell and *downloaded* lessons still work offline; sign-in still works (Supabase); browsing new chapters, submitting evidence (queued in IndexedDB), teacher dashboards and the tutor wait for the cold start. The frontend must show a "waking up" state instead of an error.
**Minimum reliable demo:** CF Pages + Render free (with a health-check ping during the demo window) + Supabase free (touched within 7 days) + Groq free. **Minimum for real students:** Render Starter + Supabase Pro + Groq paid fallback ≈ **US$32/month + AI usage**.
**Production checklist (to implement):** `FRONTEND_ORIGINS` = exact Pages domain(s); Supabase Auth Site URL + redirect URLs; fix `render.yaml` branch; migrations as a locked release step; `/api/v1/health` (liveness) vs `/api/v1/health/ready` (DB + AI reachability); structured logs without PII; rate limits per user (tutor, evidence ingest); post-deploy smoke script (`scripts/smoke_production.ps1` exists — to be updated) covering sign-up → onboarding → open lesson → answer check → teacher sees evidence.

---

## 12. Security and child privacy

- **Law:** India's DPDP Act 2023 treats everyone under 18 as a child: verifiable parental consent is required, and tracking/behavioural monitoring of children is restricted, with exemptions for educational institutions under the DPDP Rules. Adaptive learning is behavioural monitoring in a plain reading. **Recommendation:** deploy primarily through schools (school is the data fiduciary/consent channel; teacher-created classrooms; join codes), and for independent sign-ups require a guardian-consent step before any evidence is stored. **Get a legal review before real student launch — I am not a lawyer.**
- **Data minimisation:** display name (not full name), grade, board, language, age band; no DOB, phone, address, school ID, photos. Email only for the account (consider teacher-issued username accounts for students without email).
- **Access:** backend is the only data path; RLS stays deny-all for `anon`/`authenticated`; every query is scoped by `student_id` or by teacher-owns-classroom; teachers see only their classroom members; reviewer/admin roles separate. Tests assert cross-classroom isolation.
- **Fix now (low risk, needs your OK as it's a production change):** revoke `EXECUTE` on `public.rls_auto_enable()` from `anon, authenticated`; enable leaked-password protection.
- **AI:** prompts include grade, board, lesson text, last few answers — **never** name, email or IDs; tutor output is shown, not stored as mastery; rate-limited per student; refusal/redirect for off-topic or unsafe topics; check Groq's data-retention setting for the org.
- **Secrets:** server-only `SUPABASE_SECRET_KEY`, `GROQ_API_KEY`; frontend only gets the publishable key + URL. `.env` stays untracked (verified `.gitignore` exists; I did not print values).
- **Audit:** `content_audit`, recommendation provenance, teacher actions logged; export/delete-my-data endpoint.

---

## 13. Phased roadmap (each phase ends demoable and tested)

| Phase | Scope | Exit test |
|---|---|---|
| **P0 Baseline** | Commit current tree to `baseline/pre-zenith-transform` + tag; resolve name rule; start test Postgres; get pytest green or document failures | Tests run; nothing lost |
| **P1 Remove document stack** | Code, deps, routes, UI per §6; DB untouched | Build + tests green; image smaller; app boots without pipeline |
| **P2 Content core** | Migrations 009–011; schema; validator; importer; review/publish screens; Learn browse APIs; lesson reader | **One chapter** end-to-end, published only after review; drafts unreachable (test) |
| **P3 Evidence + model** | Evidence API, verification, BKT v2, Elo, item selection; Solve + Test | Unit tests on model math; replay test from fixture events |
| **P4 Adaptivity** | Prerequisite investigation, variants, next-best-action, acceleration, reviews | Scenario tests: struggler routed to Class 6 integers; fast learner skips |
| **P5 Teacher** | Class/concept/misconception views, assignments, interventions, Teach mode | Teacher sees exactly what a test student did; isolation tests |
| **P6 Tutor** | Grounded hints/explanations, multilingual explain, guardrails, outage handling | Works with AI off (graceful), Groq, LM Studio |
| **P7 Offline** | Dexie packs for published lessons + items (answers server-verified on sync for tests; local verify for practice), idempotent sync | Airplane-mode journey |
| **P8 Content production** | Runs in parallel from P2: author/review chapters to release scope | Reviewer sign-off per chapter |
| **P9 Harden & deploy** | Consent flow, rate limits, health/ready, smoke tests, deploy, then legacy-table drop (approved) | Production smoke passes |

Critical path: P0 → P1 → P2 → P3 → P4 → P5; P6/P7 after P3; **P8 is the long pole** and is gated by human review capacity, not engineering.

---

## 14. What I need from you

**Decisions**
1. Product name: ZENITH everywhere? Then you update `AGENTS.md` rule 1 (or tell me to). Repo/bucket names can stay `setu-*` internally.
2. Commit the current uncommitted work to a baseline branch before I change anything? (Strongly recommended.)
3. Boards for v1: **CBSE (NCERT 2025-26 textbooks)** only, or CBSE + Telangana State Board? Which curriculum year to target?
4. Release scope (my recommendation in §15) and which chapters.
5. Explanation languages beyond English: Hindi? Telugu? Are AI-translated explanations acceptable with a visible "AI-translated, not reviewed" label?
6. Who reviews content (subject teachers?) and how many hours/week — this sets content throughput.
7. Primary channel: school-led (teacher creates class) vs independent student sign-up; and whether you will fund Supabase Pro + Render Starter (~US$32/mo) for real students.
8. The 8 existing auth users and their 17 attempts — test accounts I can archive, or real people to preserve?
9. Gamification: OK to drop coins/XP and keep streak + chapter completion + few badges?

**Access / configuration (set in dashboards; never paste secrets in chat)**
- Backend env (Render): `DATABASE_URL` (Supabase *session* pooler for migrations, transaction pooler for app), `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER=groq`, `LLM_MODEL`, `LLM_FALLBACK_MODEL` (confirm both exist in your Groq console), `ENABLE_REMOTE_AI=true`, `FRONTEND_ORIGINS`, `APP_ENV=production`.
- Local: `SETU_TEST_DATABASE_URL` (Docker Postgres) to run tests; LM Studio: `LLM_PROVIDER=lmstudio`, `LLM_BASE_URL=http://localhost:1234/v1`, `LLM_MODEL=<loaded model id>`.
- Frontend env: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`.
- Supabase dashboard: Auth Site URL + redirect URLs for the production domain; enable leaked-password protection; confirm email confirmation policy for students.
- Vercel connector: approve team access for `leeladhar2804-2489s-projects` if you want me to manage Vercel (or choose Cloudflare Pages and give a Cloudflare account).
- Render account + whether the GitHub repo default branch should become `main` or render.yaml should use `master`.
- Groq console: your tier and rate limits; enable zero data retention if offered.
- Branding: final logo/wordmark (the `zenith-logo.svg` in `frontend/public` — is it final?), and a domain name if you have one.
- Backblaze B2: confirm we can ignore it for v1.

---

## 15. Recommended first production release (v1)

**Board:** CBSE, NCERT current editions. **Subjects:** Mathematics + Science. **Language:** English content; Hindi (and optionally Telugu) *AI explanations* labelled as such.
**Published chapters (12, chosen to form prerequisite chains across grades):**
- Maths: C6 Integers (*The Other Side of Zero*) & Fractions · C7 Algebraic Expressions (intro) & Integers operations · C8 Linear Equations in One Variable · C9 Polynomials · C10 Pair of Linear Equations & Quadratic Equations.
- Science: C6 one chapter (e.g., measurement/materials) · C7 Acids, Bases & Salts (as titled in current edition) · C8 one · C9 one · C10 Chemical Reactions & Equations.
  *(Exact titles/numbers to be verified against the current NCERT editions before authoring.)*
- Each published chapter: 4–6 lessons, ≥ 2 original figures, ≥ 3 worked examples, in-lesson checks, 25–40 practice/test items with misconception-tagged distractors, a chapter summary, reviewed by a named teacher.
- Every other chapter of the current editions for Classes 6–10 Maths/Science listed as **Coming soon** (titles only).
**Features:** sign-up with consent, onboarding (class/board/language), Learn library, lesson reader with variants, Solve + Test, BKT+Elo model, prerequisite investigation, Today recommendations, teacher class/concept/misconception views + assignments, grounded tutor with graceful offline/outage behaviour, offline download of lessons, deployed on CF Pages + Render + Supabase.
**Explicitly out of v1:** voice, video, document upload, parent app, leaderboards, non-CBSE boards, fitted model parameters (collected, not yet fitted).

Honest scale note: 12 genuinely reviewed chapters is ~50–70 lessons and ~400 items. With AI-assisted drafting and one reviewer at ~10 h/week, expect 6–10 weeks of content work. Engineering P0–P7 is roughly 4–6 weeks for one engineer-agent with you reviewing. The engineering will be ready before the content is.

---

## 16. Decisions recorded (2026-11-10) and plan changes

| # | Decision | Effect on the plan |
|---|---|---|
| D1 | Visible name **ZENITH** | `AGENTS.md` rewritten (rule 1). All user-visible "SETU" removed in P1. Repo and Supabase names stay internal. |
| D2 | **CBSE only** for v1 (current NCERT editions) | Schema stays board-agnostic; only CBSE curriculum versions are seeded. |
| D3 | Explanations in **English + Hindi + Telugu** | Lessons are authored in English. The tutor can explain in Hindi or Telugu, labelled "AI-translated, not reviewed". Reviewed translations become `lesson_versions` with `language=hi/te` later. UI strings get i18n keys from day one. |
| D4 | **School-led first, independent sign-up allowed** | Teacher classrooms with join codes. Independent students go through a guardian-consent step before any evidence is stored. |
| D5 | **Baseline** | Done: branch `baseline/pre-zenith-transform`, tag `pre-zenith-transform` (commit `4e87a73`, not pushed). Work continues on `zenith/transform`. |
| D6 | Existing 8 accounts are **test data → archive** | During the approved DB reset: back up, then clear application rows. Deleting the 8 `auth.users` is a separate step that needs approval. |
| D7 | **Build our own review engine; teachers approve** | New phase P2b (below). Nothing auto-publishes. |
| D8 | **Delete all SETU files** | P1 widens: remove the whole document product, SETU branding assets (`setu-logo.svg`, `AskSetu*`), and old SETU reports and audits in `context/`, `TEST_INFRA.md`, `TEST_READY.md`, `agents/`. Git history keeps them. |
| D9 | **Entirely free hosting, no credit card** | Revised in 16.1. |
| D10 | **Very interactive and competitive, all features** | Revised in 16.2, with child-safety guardrails. |
| D11 | **Research popular edtech sites, take the best of each, blazingly fast frontend** | New phase D (16.3) before UI implementation. |

### 16.1 Hosting revised: everything on free tiers, no card

- **Vercel Hobby** for both the frontend (static PWA) and the API (FastAPI as a Python serverless function under `/api`). One origin means no CORS; the Vercel connector is already linked. Hobby needs no card. Hobby is limited to **non-commercial** use, which fits a free product.
  - **Function constraints:**
    - Per-request time limit: confirm the current Hobby maximum. Tutor calls must stream or finish within it.
    - Bundle size limit (~250 MB unzipped): fine once PyMuPDF and friends are gone.
    - No background loops or long-lived workers.
    - Cron jobs are limited on Hobby: at most daily.
  - **Database connections:** Supabase transaction pooler (port 6543) with `NullPool` and prepared statements disabled.
- **Supabase free:** no card, but the project pauses after 7 days without activity.
  - Keep-alive: a daily Vercel cron (or GitHub Actions schedule) calls `/api/v1/health/ready`, which runs a trivial query.
  - Backups: none on free. Proposal: a weekly GitHub Actions `pg_dump`, encrypted before upload and kept for 7 days. This needs your approval, because the backup contains student data.
- **Groq free:** no card. Per-model RPM/RPD caps.
  - The tutor has a per-student daily quota.
  - Answers are cached per (lesson block, language, prompt type), so common explanations are generated once and reused.
  - If Groq is unavailable or rate-limited, the tutor falls back to the reviewed lesson content.
- **Media:** original SVG diagrams ship with the frontend (CDN cached, offline friendly). The 1 GB Supabase Storage is used only if raster images grow large. **No Render, no Cloudflare, no B2.**
- **Migrations:** run from your machine or a GitHub Action with the session pooler URL, never on function boot.
- **Honest limits:**
  - No SLA.
  - Groq's free caps may throttle a large class at peak.
  - Without paid backups, data durability relies on the weekly encrypted dump.

### 16.2 Gamification revised: competitive, with guardrails

**Build:**
- **XP** earned for learning actions, weighted toward mastery gained rather than raw clicks, plus **levels**.
- **Daily streak** with one free "rest day" per week, so no streak shaming.
- **Daily and weekly quests** ("Fix one weak concept", "3 correct in a row on a challenge item").
- **Badges** for mastery, comebacks, helping classmates and consistency.
- **Classroom leaderboard / weekly league:**
  - Ranks by **weekly XP and improvement**, so it doesn't just reward students who were already strong.
  - Shows nickname and avatar only.
  - The teacher can switch it on or off per class; students can hide themselves.
- **Class challenges:** the whole class works toward a goal, such as "80% of us secure on Integers by Friday".
- **Asynchronous concept duels:** two classmates get the same adaptive item set and results are compared later.
- **Timed "speed rounds"** for revision, as an optional mode.
- **Chapter mastery trophies** and visible progress on the concept map.
- **Teacher-set rewards** ("Top improvers this week") and **celebration moments** with lightweight animation, respecting reduced motion.

**Guardrails (children 11–16):**
- No public or global leaderboard with names; leaderboards are only within a classroom.
- No purchasable items, no loot boxes, no real money.
- Competitive XP never affects mastery or teacher evidence.
- Tests and reassessments are never timed competitively.
- Every competitive feature is opt-out.

### 16.3 Phase D: design research and system (before UI build)

- **Survey** the public pages of: Canvas Classes (already fetched), Khan Academy, Brilliant, Duolingo, Quizlet, Seneca Learning, Physics Wallah, BYJU'S, Vedantu and Toppr.
- **Capture** their information architecture, lesson anatomy, feedback moments, gamification, mobile navigation and performance (Lighthouse on mobile).
- **Output:**
  - A design brief: what to take from each and what to avoid.
  - ZENITH tokens: colour, type scale, spacing, radii, motion and subject palettes.
  - Component inventory.
  - Key screen mockups (Today, Learn browse, Lesson reader, Practice, Concept map, League, Teacher class view, Review queue), presented for your sign-off.
- **Performance budget:**
  - Initial JS ≤ 170 kB gzip.
  - LCP < 2.5 s on a mid-range Android over 4G.
  - Interaction latency < 100 ms.
  - Fonts self-hosted and subset (Latin + Devanagari + Telugu, loaded on demand).
  - Images as SVG/WebP.

### 16.4 Phase P2b: review engine

- **Automated gates:**
  - JSON schema validation.
  - SymPy verification of every maths answer and worked-example step.
  - Distractor sanity checks (exactly one correct answer, no duplicate options).
  - Readability scored against grade level.
  - KaTeX parse.
  - Alt text and licence present on every image.
  - Prerequisite DAG acyclic.
  - Curriculum mapping present.
  - AI reviewer pass: a rubric covering factual accuracy, age-appropriateness, misconception coverage and clarity, which produces **flags only, never approval**.
- **Teacher review UI:**
  - The queue shows each lesson exactly as a student sees it, with gate results and AI flags inline.
  - Teachers can comment per block.
  - Actions: approve, request changes, or edit then approve.
- **Publishing rule:** publish requires all gates passing plus an approval from a user with the `reviewer` role, enforced by a DB constraint.

### 16.5 Revised phase order

P0 done (baseline) → **P1** remove SETU/document stack → **D** design research and system (in parallel with P2) → **P2** content core + **P2b** review engine → **P3** evidence and model → **P4** adaptivity → **P5** teacher → **P5b** gamification and competition → **P6** tutor (multilingual) → **P7** offline → **P8** content production (parallel from P2) → **P9** hardening and Vercel deploy.
