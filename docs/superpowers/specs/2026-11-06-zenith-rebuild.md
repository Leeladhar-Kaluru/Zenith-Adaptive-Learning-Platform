# ZENITH Rebuild — Product & Technical Specification

**Date:** 2026-11-06  
**Status:** Draft for approval  
**Repo:** `C:\projects\setu - V2`  
**Baseline commit:** `a3473f8`  
**Working name:** ZENITH (visible product name; never “ZENITH V2” or “ZENITH 2.0”)

---

## 1. Executive summary

ZENITH is an AI-powered adaptive learning product for Indian students in Classes 6–10. It combines a real, database-backed original Learning Library with evidence-based diagnostics, prerequisite-aware practice, a grounded AI tutor, and a calm, motivating study experience.

This rebuild keeps the working React 19 + Vite + TypeScript + CSS Modules frontend, FastAPI backend, Supabase PostgreSQL/Auth/Storage, pgvector, LM Studio compatibility, and all existing data. It rebrands every user-facing surface from SETU to ZENITH and shifts the product from “upload a textbook first” to “open a library and start learning.”

The flagship library is **CBSE Class 10 Mathematics, four chapters, five published resources per chapter**. This is deliberately a high-quality founding library, not a claim of full CBSE coverage. Every chapter is labelled as part of the founding collection, and empty subjects show an honest “request this subject” path instead of fabricated content.

**What ships in this rebuild**

- A library-first student home, Explore, chapter pages, reader, My Learning, Practice Arena, Learning Map, Achievements, Profile, and Ask Zenith.
- A real content pipeline: typed/versioned JSON packages, deterministic validation, idempotent seeding, publication audit, and rollback.
- Concept DAG, evidence-based diagnostic sessions, prerequisite gap detection, proper BKT in shadow mode, and rewards that are idempotent.
- A provider-agnostic AI layer (Groq in production, LM Studio locally) with citations, quotas, and honest failure states.
- Preserved teacher classroom workflows and existing uploaded-document flows, moved to a secondary `/sources` area.
- Production deployment configuration and a local production smoke test. Actual cloud deployment remains pending account credentials.

---

## 2. Repository audit (verified 2026-11-06)

### 2.1 What already works

| Area | Verified state |
|---|---|
| Frontend | React 19 + Vite 6 + TypeScript + CSS Modules; production build passes (`596.40 kB` JS, `181.48 kB` gzip); PWA plugin builds |
| Backend | FastAPI app, SQLAlchemy models, Alembic migrations, Supabase Auth verification, privileged DB session |
| Database | Supabase project `mevbffduofdpalzimfye`, region `ap-south-1`, healthy; Alembic revision `008` |
| Data | 6 boards, 6 subjects, 4 languages, 8 profiles, 2 documents, 6 learning paths, 66 lessons, 528 questions, 17 attempts, 10 classrooms, 0 catalogue resources |
| Learning engine | Deterministic `rules-v1` mastery bands, attempt grading, concept evidence, smart-check question selection, remediation injection for personal paths |
| AI | OpenAI-compatible chat/embeddings client; LM Studio default; Groq `openai/gpt-oss-120b` tested successfully with the existing `GROQ_API_KEY` |
| Offline | Dexie `SetuDeskDB`, cached lessons, attempt outbox, doubt outbox, reconnect sync |
| Tests | 197 backend test functions; 20 Playwright tests; backend suite requires disposable PostgreSQL on port `55432` |
| Security | Supabase JWT verification; RLS enabled on all public tables with zero policies (default deny); backend uses a privileged role that bypasses RLS |

### 2.2 Gaps this rebuild must close

1. **No real library.** `resources` is empty; the current home page is upload-first. There is no curriculum hierarchy, publication workflow, or quality gate for first-party content.
2. **No adaptive depth.** Mastery is a hand-weighted rules heuristic. There is no BKT, no concept DAG, and no prerequisite diagnosis.
3. **No rewards loop.** No XP, coins, badges, streaks, or durable motivation layer.
4. **Weak AI integration.** `GROQ_API_KEY` is unused; LM Studio is down by default; there is no provider abstraction, quota, or resource-aware citation path.
5. **Brand is still SETU.** Titles, manifest, navigation, onboarding, tests, README, and copy all say SETU.
6. **No production packaging.** No `backend/requirements.txt`, Dockerfile, Render config, or Cloudflare Pages config.
7. **Navigation is thin.** Home, Dashboard, Lesson, Downloads, Doubts, Teacher. No Explore, chapter pages, Practice Arena, Learning Map, Achievements, or Profile.
8. **Concept labels are unreadable for scoped IDs.** `cbse-10-math--hcf-and-lcm` currently renders as “Cbse 10 math hcf and lcm.”
9. **Library content cannot reuse attempts yet.** `grade_and_record_attempt` requires `path.owner_id == owner_id`; library paths need a system owner and an explicit public-read policy.
10. **Remediation injection would mutate published library content.** It must be disabled for library paths.

### 2.3 Hard constraints

- Do not delete or rewrite existing user data, documents, attempts, classrooms, or profiles.
- Keep external Supabase project, storage bucket `setu-documents`, env var names (`SETU_*`), localStorage key `setu_auth_token`, and IndexedDB database `SetuDeskDB` unchanged to preserve sessions and offline data.
- No hardcoded production users, progress, analytics, subjects, boards, languages, or classroom memberships.
- No NCERT or textbook rehosting. All library content is original, authored for ZENITH, with `sourceRefs: []` where no external source is used.
- Frontend stays React 19 + Vite + TypeScript + CSS Modules. No Tailwind v4, no shadcn.
- Backend stays FastAPI + Supabase PostgreSQL/Auth/Storage + PostgreSQL full-text + pgvector(768).
- Never expose service-role keys or secrets to the browser.

---

## 3. Product definition

### 3.1 Vision

> Every student should know what to study next — and why.

ZENITH turns a vague “study more” instruction into a specific next step: read this explanation, practise this concept, fix this prerequisite, then try a harder question. The product is calm and evidence-led. It never invents progress, mastery, or urgency.

### 3.2 Audience

- **Primary:** Indian students in Classes 6–10, starting with CBSE Class 10 Mathematics.
- **Secondary:** Teachers who need a clear evidence view of their classroom.
- **Tertiary:** Parents/guardians who want honest progress signals (read-only surfaces only if added later; not in this scope).

### 3.3 Product principles

1. **Evidence before advice.** Every recommendation names the evidence behind it or says “not enough evidence yet.”
2. **Library before upload.** A student can learn immediately without owning a textbook PDF.
3. **One clear next step.** Home, chapter pages, and Practice Arena all converge on the same next-best action.
4. **Teach the prerequisite.** A wrong answer on a hard concept does not automatically mean the student is “bad” at it; the product checks the foundation first.
5. **Warm, not gamified noise.** Rewards recognise effort and return visits, not compulsive loops. No fake leaderboards, no loss-framed streaks, no dark patterns.
6. **Honest AI.** The tutor cites the library or uploaded source it used, admits when it cannot ground an answer, and never leaks answer keys.
7. **Works offline.** Reading, practice, and doubts survive a dropped connection; sync is idempotent.

### 3.4 Non-goals for this rebuild

- Full CBSE/ICSE/State coverage for every class and subject.
- Image-based doubt solving, handwriting OCR, or voice tutoring.
- Live classes, payments, parent accounts, or school admin console.
- A public content marketplace or third-party content ingestion.
- Claiming production deployment success without credentials and verification.

---

## 4. Brand and design direction

### 4.1 Brand

- **Name:** ZENITH
- **Tagline:** *Your peak, within reach.*
- **Descriptor:** *Adaptive learning for Classes 6–10*
- **Promise:** *Know what to study next — and why.*
- **Voice:** calm, precise, encouraging. Short sentences. No hype, no “magic”, no “unlock your potential”, no fake urgency.
- **Visual metaphor:** a topographic trail to a summit. Contour lines, elevation markers, a rising path, a summit point.

### 4.2 Logo

A custom SVG mark: three ascending strokes form a “Z” and a mountain ridge; a gold summit dot sits at the top right. The wordmark uses Fraunces SemiBold with slight positive tracking. The mark must work at 24 px, 34 px, and 512 px, in mono and full colour.

Files: `frontend/public/zenith-mark.svg`, `frontend/public/zenith-logo.svg`, PWA icons `frontend/public/pwa-192.png`, `pwa-512.png`, `apple-touch-icon.png`, maskable icon.

### 4.3 Palette

| Token | Value | Use |
|---|---|---|
| `--bg-canvas` | `#F7F4EC` | warm paper canvas |
| `--bg-surface` | `#FFFFFF` | cards, sheets |
| `--ink-primary` | `#10202B` | primary text |
| `--ink-secondary` | `#46545F` | secondary text |
| `--brand-primary` | `#0C6B5F` | primary actions, links |
| `--brand-primary-hover` | `#09564C` | hover |
| `--brand-deep` | `#0B1F2A` | dark rails, hero |
| `--accent-warm` | `#D99A1B` | summit gold, highlights |
| `--accent-warm-ink` | `#5A3B00` | text on gold |
| `--bg-accent-subtle` | `#FBF0D9` | gold-tinted surfaces |
| `--color-success` | `#1B7A52` | correct, secure |
| `--color-warning` | `#9A5B00` | needs review |
| `--color-error` | `#B3261E` | errors |
| `--color-info` | `#1D5FA8` | informational |

Gold is never used for small text on white. It is used for large numerals, icons on dark, progress fills, and surfaces with dark text. All text pairs must meet WCAG 2.2 AA (4.5:1 body, 3:1 large).

Subject accents: Mathematics gold `#B87400`, Science teal `#0C6B5F`, Social Science terracotta `#B44D32`, English indigo `#5B46B8`, Hindi rose `#A83A63`, IT blue `#1D5FA8`. Each is paired with a text label, never colour alone.

### 4.4 Typography

- Display: **Fraunces** (600/700), fallback Georgia.
- UI/body: **Plus Jakarta Sans** (400/500/600/700), fallback system-ui.
- Reading: **Literata** (400/500), 1.7 line height, max 68ch.
- Numerals: **JetBrains Mono** for stats and timers.

Fonts load with `display=swap`; critical UI text must remain readable if fonts fail.

### 4.5 Shape, layout, motion

- Radii: 10/14/18/24 px. Less bubbly than the old desk, still friendly.
- Sidebar 248 px; content max 1180 px; 12-column grid.
- Mobile: 5-item bottom nav (Home, Explore, Practice, Map, Ask), sidebar becomes a drawer.
- Motion: 180–240 ms ease-out; 8 px page rise; progress ring animation; badge celebration only on award. Respect `prefers-reduced-motion`.
- Background: warm paper with a faint topographic contour pattern, not a generic gradient blob.
- Illustrations: geometric contour lines, subject glyphs, and diagram primitives. No stock photos of students; no AI-generated faces.

### 4.6 Accessibility

- WCAG 2.2 AA contrast, 44×44 px targets, visible focus rings, semantic headings, labelled forms.
- Status is never colour-only: icon + label.
- Respect the existing accessibility preferences: font size, reduced motion, high contrast, pace.
- Keyboard-complete dialogs, drawers, and the Learning Map side panel.

---

## 5. Information architecture and journeys

### 5.1 Student routes

| Route | Page | Purpose |
|---|---|---|
| `/` | Home | Greeting, continue learning, daily goal, next best action, streak, recommended chapter |
| `/explore` | Explore | Search/filter the library by board, class, subject; chapter cards; honest empty states |
| `/chapter/:slug` | Chapter | Overview, outcomes, concept map preview, 5 resources, diagnostic CTA, progress |
| `/learn/:lessonId` | Reader | Read a resource, navigate sections, take practice/checkpoint, save offline, ask about a section |
| `/my-learning` | My Learning | Enrolled chapters, progress, continue, completed, offline downloads |
| `/practice` | Practice Arena | Diagnostic, smart practice, weak-concept drill, mixed check |
| `/map` | Learning Map | Concept DAG with evidence status, prerequisite gaps, resource links |
| `/achievements` | Achievements | XP, level, coins, streak calendar, badges, recent rewards |
| `/profile` | Profile | Academic context, goals, accessibility, AI/data controls, sign out |
| `/ask` | Ask Zenith | Tutor threads, grounded answers, citations, offline queue |
| `/sources` | Sources | Existing upload/ingest/generate flows (old HomePage), clearly secondary |
| `/teacher` | Teacher | Preserved classroom dashboard, roster, evidence matrix, messages |
| `/onboarding` | Onboarding | First-run flow; also available as a modal from Home |

Legacy redirects: `/dashboard` → `/my-learning`; `/doubts` → `/ask`; `/library` → `/my-learning?tab=offline`.

### 5.2 First-run journey

1. Student signs in / creates an account.
2. Onboarding asks: name → class + board → subjects + goal → daily goal → finish.
3. If the selected context has library content (CBSE 10 Maths), offer a 8–10 question diagnostic.
4. If not, show an honest empty state: “The founding library currently covers CBSE Class 10 Mathematics. Request your subject and we’ll prioritise it.” Persist the request.
5. Home shows the diagnostic card or the first chapter, never fake progress.

Onboarding is skippable, resumable, and editable in Profile. It persists to `user_profiles` through the existing profile API.

### 5.3 Core learning loop

```
Home next action
  → Chapter / resource
  → Read explanation + worked examples
  → Practice 3–8 questions
  → Server grades, records evidence, updates BKT/rules, awards XP
  → Feedback + explanation + next action
  → Learning Map updates
  → Next action becomes harder, or prerequisite remediation
```

### 5.4 Teacher journey

Preserved: sign in as teacher → classroom list → create/join code → roster → evidence matrix → recommendation → classroom messages. Add readable concept labels and library chapter context to the evidence matrix. Teachers do not see student AI chat content.

---

## 6. Learning Library

### 6.1 Hierarchy

```
Board (CBSE)
  → Grade (10)
    → Subject (Mathematics)
      → Chapter (Real Numbers)
        → Concept DAG
        → Resource (detailed lesson, worked examples, quick revision, formula sheet, practice set)
          → LessonVersion (versioned package)
            → Questions
```

`LearningPath` represents a **chapter**. `PathLesson` represents a **resource**. This reuses attempts, mastery, smart-check, offline packs, and teacher evidence without a parallel content system.

### 6.2 Flagship scope

**CBSE Class 10 Mathematics, 4 chapters, 5 published resources each = 20 published resources.**

| # | Chapter | Resources |
|---|---|---|
| 1 | Real Numbers | Detailed lesson, worked examples, quick revision, formula sheet, practice set |
| 2 | Polynomials | Detailed lesson, worked examples, quick revision, formula sheet, practice set |
| 3 | Pair of Linear Equations in Two Variables | Detailed lesson, worked examples, quick revision, formula sheet, practice set |
| 4 | Quadratic Equations | Detailed lesson, worked examples, quick revision, formula sheet, practice set |

Each chapter also has a hidden diagnostic bank (foundation bridge + core questions) that is **not** shown as a resource.

Content volume target per chapter:

- Detailed lesson: 700–900 words, 5–7 sections, 2–3 worked examples, 3–5 takeaways.
- Worked examples: 4–5 fully solved examples with steps and a “why this step” note.
- Quick revision: 300–400 words, key ideas, common mistakes, 5 rapid checks.
- Formula sheet: 150–250 words/expressions, conditions and when to use each formula.
- Practice set: 6–8 questions across introductory/standard/challenge, with hints and feedback.
- Diagnostic bank: 4 foundation bridge questions + 4 core questions per chapter.

All content is original. Where a definition is standard mathematical knowledge, it is written in ZENITH’s own words. `sourceRefs` is `[]`; the manifest records `rights: "original"` per chapter/resource and the validator allows the empty array only in that case. The lesson-package schema itself has no `rights` field.

#### 6.2.1 Concept inventory (30 concepts)

| Chapter | Core concepts | Foundation concepts |
|---|---|---|
| Real Numbers | `cbse-10-math--euclids-division-lemma`, `--fundamental-theorem-arithmetic`, `--hcf-and-lcm`, `--irrational-numbers`, `--decimal-expansions` | `cbse-9-math--number-systems`, `--exponents-and-radicals` |
| Polynomials | `cbse-10-math--polynomials`, `--degree-and-coefficients`, `--zeros-of-a-polynomial`, `--zeros-coefficient-relations`, `--division-algorithm-polynomials`, `--factor-and-remainder-theorems` | `cbse-9-math--polynomial-basics`, `--algebraic-identities` |
| Pair of Linear Equations | `cbse-10-math--linear-equations-two-variables`, `--graphical-method`, `--substitution-elimination`, `--consistency-of-pairs`, `--linear-word-problems` | `cbse-8-math--linear-equations-one-variable`, `cbse-9-math--coordinate-geometry-basics` |
| Quadratic Equations | `cbse-10-math--quadratic-equations`, `--factorisation-method`, `--completing-the-square`, `--quadratic-formula`, `--discriminant-and-roots`, `--quadratic-word-problems` | `cbse-9-math--factorisation`, `--quadratic-polynomials` |

Prerequisite edges (foundation → chapter concept, then within-chapter order):

- `number-systems` → `euclids-division-lemma`, `fundamental-theorem-arithmetic`; `euclids-division-lemma` and `fundamental-theorem-arithmetic` → `hcf-and-lcm`; `fundamental-theorem-arithmetic` and `exponents-and-radicals` → `irrational-numbers`; `irrational-numbers` → `decimal-expansions`.
- `polynomial-basics` → `polynomials`; `polynomials` → `degree-and-coefficients` → `zeros-of-a-polynomial` → `zeros-coefficient-relations`; `polynomials` → `division-algorithm-polynomials`; `algebraic-identities`, `division-algorithm-polynomials`, and `zeros-of-a-polynomial` → `factor-and-remainder-theorems`.
- `linear-equations-one-variable` → `linear-equations-two-variables`; `coordinate-geometry-basics` and `linear-equations-two-variables` → `graphical-method`; `linear-equations-two-variables` → `substitution-elimination`; `graphical-method` and `substitution-elimination` → `consistency-of-pairs`; `linear-equations-two-variables` and `substitution-elimination` → `linear-word-problems`.
- `factorisation` and `quadratic-polynomials` → `quadratic-equations`; `quadratic-equations` → `factorisation-method`, `completing-the-square`, `quadratic-formula`; `quadratic-formula` → `discriminant-and-roots`; `factorisation-method` and `quadratic-formula` → `quadratic-word-problems`.
- Cross-chapter: `factor-and-remainder-theorems` → `factorisation-method`; `zeros-of-a-polynomial` → `quadratic-polynomials`.

### 6.3 Content files

```
backend/app/content/library/
  manifest.json
  cbse-10-math/
    chapter.json
    real-numbers/
      lesson.json
      worked-examples.json
      quick-revision.json
      formula-sheet.json
      practice-set.json
      diagnostic-bank.json
    polynomials/...
    linear-equations/...
    quadratic-equations/...
```

`manifest.json` declares board, grade, subject, chapters, concepts, prerequisite edges, resource order, and content version. Each resource JSON conforms to the existing lesson-package schema with `sourceRefs: []` and `validation.status: "ready"`.

### 6.4 Publication workflow

1. Author edits JSON.
2. `python -m scripts.validate_library` runs JSON Schema + semantic checks.
3. `python -m scripts.seed_library --dry-run` prints the diff.
4. `python -m scripts.seed_library --publish` upserts chapters/resources/questions in one transaction and records a `library_publication_events` row per resource.
5. `python -m scripts.publish_library --rollback <event-id>` restores the previous published version.
6. The API only serves `learning_paths.library_status = 'published'` and `lesson_versions.validation_status = 'ready'`.

Validation checks:

- Schema conformance, required fields, max lengths.
- Unique `lessonId`, `questionId`, `blockId`, resource kind per chapter.
- Concept IDs referenced by questions exist in the manifest.
- Prerequisite graph is acyclic; every edge references known concepts.
- MCQ: ≥2 options, answer key present in options, no duplicate options.
- Numeric: answer key parses as a number; tolerance declared where needed.
- Short text: accepted answers non-empty; no answer key echoed in prompt.
- Word counts and resource-kind-specific minimums.
- No placeholder strings (`TODO`, `TBD`, `lorem ipsum`, `[insert`).
- No duplicate question prompts within a chapter.
- Every concept has at least one teaching resource and one question.
- `validation.status` is `ready`; `sourceRefs: []` is allowed only when the manifest declares `rights: "original"` for that chapter/resource. The lesson-package schema has no `rights` field, so rights live in the manifest, not the package.

### 6.5 Idempotency and versioning

- Chapter key: `library_slug` (e.g. `cbse-10-math-real-numbers`).
- Resource key: `lesson_key` (e.g. `real-numbers--detailed-lesson`).
- Content hash: SHA-256 of canonical JSON.
- If hash is unchanged, seed does nothing.
- If changed, create a new `LessonVersion` with `version_number + 1`; keep the old version.
- `published_at` and `validation_report_json` are stored on the new version.
- Re-running seed never duplicates chapters, lessons, versions, or questions.

---

## 7. Data model

### 7.1 Changes to existing tables

`learning_paths`:

- `is_library BOOLEAN NOT NULL DEFAULT false`
- `library_slug VARCHAR(120) NULL UNIQUE`
- `library_status VARCHAR(20) NOT NULL DEFAULT 'draft'` (`draft`, `published`, `archived`)
- `board_id VARCHAR(50) NULL`
- `description TEXT NULL`
- `cover_json JSON NULL`
- `published_at TIMESTAMPTZ NULL`
- `content_version VARCHAR(20) NULL`
- partial unique index on `library_slug` where not null
- index on `(is_library, library_status, board_id, grade, subject_id)`
- chapter title, chapter number, learning outcomes, and concept order stay in the existing non-null `outline_json`; no separate title column is added. `library_slug` is the stable public key.

`path_lessons`:

- `resource_kind VARCHAR(40) NULL` (`detailed_lesson`, `worked_examples`, `quick_revision`, `formula_sheet`, `practice_set`, `diagnostic_bank`)
- `summary VARCHAR(500) NULL`
- `estimated_minutes INTEGER NULL`
- `is_preview BOOLEAN NOT NULL DEFAULT false`
- index on `(path_id, resource_kind)`

`lesson_versions`:

- `published_at TIMESTAMPTZ NULL`
- `validation_report_json JSON NULL`
- `content_hash VARCHAR(64) NULL`
- unique `(path_lesson_id, version_number)`

`questions`:

- `explanation TEXT NULL`
- index on `(lesson_version_id, question_key)` unique

### 7.2 New tables

**Concepts and DAG**

- `concepts`: `id VARCHAR(100) PK`, `label VARCHAR(120)`, `description TEXT`, `board_id`, `grade`, `subject_id`, `chapter_slug`, `is_foundation BOOLEAN`, `created_at`.
- `concept_edges`: `id UUID PK`, `from_concept_id`, `to_concept_id`, `relation VARCHAR(30) DEFAULT 'prerequisite'`, `reason VARCHAR(300)`, `strength FLOAT DEFAULT 1.0`, unique `(from_concept_id, to_concept_id, relation)`, check `from != to`.
- `concept_chapters`: `concept_id`, `path_id`, `sequence`, unique `(concept_id, path_id)`.

**Enrollment and progress**

- `library_enrollments`: `id`, `owner_id`, `path_id`, `status` (`active`, `completed`, `paused`), `started_at`, `last_opened_at`, `completed_at`, unique `(owner_id, path_id)`.
- `resource_progress`: `id`, `owner_id`, `path_id`, `lesson_id`, `status` (`not_started`, `reading`, `completed`), `percent`, `last_position_json`, `completed_at`, `updated_at`, unique `(owner_id, lesson_id)`.

**Mastery**

- `bkt_states`: `id`, `owner_id`, `concept_id`, `model_variant` (`bkt_v1`), `p_known`, `p_init`, `p_transit`, `p_guess`, `p_slip`, `evidence_count`, `correct_count`, `last_attempt_at`, `updated_at`, unique `(owner_id, concept_id, model_variant)`.
- `bkt_events`: `id`, `owner_id`, `concept_id`, `attempt_id`, `model_variant`, `p_before`, `p_after`, `is_correct`, `score`, `hints_used`, `difficulty`, `occurred_at`; index `(owner_id, concept_id, occurred_at)`.

**Rewards**

- `student_rewards`: `owner_id PK`, `xp_total`, `coins_balance`, `level`, `streak_current`, `streak_longest`, `last_activity_on DATE`, `updated_at`.
- `reward_events`: `id`, `owner_id`, `kind` (`xp`, `coins`), `amount`, `reason`, `ref_type`, `ref_id`, `idempotency_key`, `created_at`, unique `(owner_id, idempotency_key)`.
- `badges`: `id`, `code`, `title`, `description`, `icon`, `criteria_json`, `sort_order`, `is_active`.
- `student_badges`: `id`, `owner_id`, `badge_id`, `awarded_at`, `evidence_json`, unique `(owner_id, badge_id)`.

**Diagnostics**

- `diagnostic_sessions`: `id`, `owner_id`, `path_id`, `status` (`in_progress`, `completed`, `abandoned`), `plan_json`, `summary_json`, `started_at`, `completed_at`, `expires_at`.
- `diagnostic_items`: `id`, `session_id`, `sequence`, `question_id`, `lesson_version_id`, `concept_ids_json`, `response_json`, `is_correct`, `score`, `hints_used`, `answered_at`, unique `(session_id, sequence)`.

**Tutor**

- `tutor_threads`: `id`, `owner_id`, `title`, `chapter_slug`, `created_at`, `updated_at`.
- `tutor_messages`: `id`, `thread_id`, `role` (`user`, `assistant`), `content`, `citations_json`, `provider`, `model`, `latency_ms`, `created_at`.
- `content_requests`: `id`, `owner_id`, `board_id`, `grade`, `subject_id`, `note`, `status` (`open`, `planned`, `declined`), `created_at`, unique `(owner_id, board_id, grade, subject_id)`.

**Publication audit**

- `library_publication_events`: `id`, `path_id`, `lesson_id`, `lesson_version_id`, `action` (`publish`, `rollback`, `archive`), `actor`, `notes`, `created_at`.

### 7.3 System owner

`LIBRARY_OWNER_ID = 00000000-0000-0000-0000-000000000001`. It owns all library `learning_paths`. No auth profile is required. `owner_id` has no FK to auth users, so this is safe. All API responses must never expose the system owner as a real person.

### 7.4 RLS posture

Existing public tables have RLS enabled with no policies; the backend uses a privileged connection that bypasses RLS. New tables must match this posture: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` in migration 009, no permissive policies. Document that the backend is the access-control boundary and that direct anon-key access is denied. Add tests that a student cannot read another student’s personal path, attempts, diagnostics, rewards, or tutor threads through the API.

---

## 8. Backend architecture and APIs

### 8.1 New modules

```
app/models/library.py          concepts, edges, enrollments, progress, publication events, content requests
app/models/mastery.py          bkt_states, bkt_events
app/models/rewards.py          student_rewards, reward_events, badges, student_badges
app/models/diagnostics.py      diagnostic_sessions, diagnostic_items
app/models/tutor.py            tutor_threads, tutor_messages
app/services/library_access.py access policy for library vs personal paths
app/services/library_service.py catalogue, chapter, resource, enrollment, progress
app/services/library_validator.py schema + semantic validation
app/services/library_seed.py   idempotent upsert/publish/rollback
app/services/bkt.py            pure BKT math
app/services/mastery_service.py rules + BKT composition, snapshots
app/services/prerequisite_service.py DAG traversal and gap detection
app/services/rewards_service.py XP, coins, levels, streaks, badges
app/services/diagnostic_service.py plan, answer, complete, summary
app/services/library_retrieval.py keyword/FTS retrieval over published packages
app/services/tutor_service.py  prompt, citations, quota, persistence
app/api/v1/library.py
app/api/v1/diagnostics.py
app/api/v1/rewards.py
app/api/v1/tutor.py
```

### 8.2 Access policy

`library_access.py`:

```python
LIBRARY_OWNER_ID: uuid.UUID

def can_read_path(path: LearningPath, user_id: uuid.UUID) -> bool:
    # published library content: any authenticated user
    # personal content: owner only
    # draft/archived library content: nobody through the public API

def resolve_readable_lesson(db, lesson_ref: str, user_id: uuid.UUID, path_id: uuid.UUID | None = None) -> PathLesson

def require_readable_path(db, path_id: uuid.UUID, user_id: uuid.UUID) -> LearningPath
```

Update all owner-only checks in `attempt_service.py`, `study.py`, `learning_paths.py`, `smart_check.py`, and `coach_service.py` to use this policy. Library paths must:

- allow attempts by any authenticated student,
- allow study events and progress,
- allow smart-check and coaching,
- **never** inject remediation lessons or enqueue generation jobs,
- never expose the system owner.

### 8.3 Library API

`GET /api/v1/library/catalogue`

Query: `board_id`, `grade`, `subject_id`, `q`, `limit` (default 24, max 48), `offset`.

Response:

```json
{
  "items": [{
    "slug": "cbse-10-math-real-numbers",
    "title": "Real Numbers",
    "description": "…",
    "board": {"id": "board-cbse", "name": "CBSE"},
    "grade": 10,
    "subject": {"id": "subject-math", "name": "Mathematics"},
    "chapterNumber": 1,
    "conceptCount": 7,
    "resourceCount": 5,
    "estimatedMinutes": 95,
    "progress": {"enrolled": true, "completedResources": 2, "percent": 40}
  }],
  "total": 4,
  "filters": {"boards": [], "grades": [], "subjects": []}
}
```

`progress` is `null` for anonymous callers. Only published chapters and ready versions are returned.

`GET /api/v1/library/chapters/{slug}` — chapter detail with outcomes, concepts, resources, progress, diagnostic availability, next action.

`GET /api/v1/library/resources/{lesson_id}` — resource package with answer keys redacted, `lessonVersionId`, `resourceKind`, `progress`. 404 for draft/unpublished.

`POST /api/v1/library/chapters/{slug}/enroll` — idempotent enrollment; returns progress.

`GET /api/v1/library/me` — enrolled chapters with progress, last opened, completed resources.

`PATCH /api/v1/library/resources/{lesson_id}/progress` — body `{status, percent, position}`; validates status transitions; records a `StudyEvent` only when completed.

`GET /api/v1/library/map?chapter=slug` — nodes and edges with status, pKnown, evidenceCount, resourceId, layer, order.

`GET /api/v1/library/concepts/{concept_id}` — concept detail, prerequisites, dependents, resources, evidence summary.

`POST /api/v1/library/requests` — body `{boardId, grade, subjectId, note}`; idempotent per user/context.

### 8.4 Diagnostics API

`POST /api/v1/diagnostics/start` body `{chapterSlug}` → `{sessionId, question, progress}`.

`POST /api/v1/diagnostics/{id}/answer` body `{questionKey, response, hintsUsed, elapsedSeconds}` → `{isCorrect, feedback, correctAnswer, nextQuestion, progress, reward}`.

`POST /api/v1/diagnostics/{id}/complete` → `{sessionId, status, summary}`.

`GET /api/v1/diagnostics/{id}` → resume payload or completed summary.

`GET /api/v1/diagnostics/latest?chapterSlug=` → latest completed summary.

Rules:

- 6 core questions + up to 4 adaptive prerequisite questions; max 10.
- No answer key before submission.
- One wrong answer is an “early signal”, not a mastery verdict.
- Completion writes evidence and a mastery snapshot; it does not fabricate a score.
- Session expires after 24 hours; expired sessions return 410.

### 8.5 Rewards API

`GET /api/v1/rewards/me` → XP, level, next level, coins, streak, weekly XP, badges, recent events.

`GET /api/v1/rewards/calendar?days=28` → activity days from `StudyEvent` and `reward_events`.

`GET /api/v1/rewards/badges` → earned and available badges with criteria and progress.

`POST /api/v1/rewards/claim-daily` — optional; awards the daily goal once when the profile goal is met. If the goal is not met, return `{awarded: false, remainingSeconds}`.

### 8.6 Tutor API

`POST /api/v1/tutor/ask` body `{question, chapterSlug?, lessonId?, threadId?}`.

Response includes `threadId`, `messageId`, `answer`, `citations`, `grounded`, `provider`, `model`, `remainingToday`.

`GET /api/v1/tutor/threads`, `GET /api/v1/tutor/threads/{id}`, `DELETE /api/v1/tutor/threads/{id}`.

Rules:

- Retrieve at most 4 library excerpts; if an uploaded document is selected, retrieve at most 3 chunks.
- Cite only retrieved material. If nothing is retrieved, answer with a general explanation and `grounded: false`, or say the library does not cover it.
- Never include answer keys, hidden test answers, or another student’s data.
- Daily quota from `AI_DAILY_MESSAGE_LIMIT` (default 30). Return 429 with `retryAfter`.
- Provider errors return 503 with a safe message and `retryable: true`; never leak the API key or upstream body.

### 8.7 Health

`GET /api/v1/health` returns:

```json
{
  "status": "ok|degraded",
  "database": {"connected": true},
  "storage": {"connected": true},
  "ai": {
    "provider": "groq",
    "chatModel": "openai/gpt-oss-120b",
    "chatReady": true,
    "embeddingProvider": "none",
    "embeddingReady": false,
    "detail": null
  },
  "library": {"publishedChapters": 4, "publishedResources": 20}
}
```

Health never returns URLs with credentials, keys, or raw upstream errors.

---

## 9. Adaptive learning

### 9.1 BKT

Implement standard Bayesian Knowledge Tracing per concept:

- Defaults: `p_init=0.25`, `p_transit=0.15`, `p_guess=0.20`, `p_slip=0.10`.
- Difficulty adjustment: introductory `guess=0.25/slip=0.08`, standard `0.20/0.10`, challenge `0.15/0.15`.
- Correct observation:
  `posterior = p*(1-slip) / (p*(1-slip) + (1-p)*guess)`
- Incorrect observation:
  `posterior = p*slip / (p*slip + (1-p)*(1-guess))`
- Learning transition: `p_next = posterior + (1-posterior)*p_transit`.
- Hints: blend the posterior toward the prior by `0.6 ** hints`, capped at 3 hints, so hinted correct answers count less.
- Partial credit: use `score` as a mixture of correct/incorrect likelihoods.
- Store every update in `bkt_events` with `p_before`/`p_after`.

**Shadow mode is the default.** `BKT_MODE=shadow` computes BKT for every new evidence row but the UI continues to use `rules-v1` bands. `BKT_MODE=active` uses BKT when evidence_count ≥ 3, with rules as fallback. The snapshot explanation includes both models so the product can be audited.

`scripts/compare_bkt.py` reports Brier score and calibration buckets from `bkt_events`. No UI claim of “better” until the comparison supports it.

### 9.2 Mastery composition

`mastery_service.get_mastery(db, owner_id, concept_id)` returns the existing shape plus:

```json
{
  "band": "developing",
  "score": 0.42,
  "evidenceCount": 4,
  "primaryModel": "rules-v1",
  "shadow": [{"model": "bkt_v1", "pKnown": 0.51, "brier": null}],
  "explanation": "…"
}
```

`attempt_service` calls `mastery_service.record_observation(...)` for each concept instead of directly calling `adaptive_engine`. The rules engine remains the fallback and the source of the human-readable explanation.

### 9.3 Prerequisite gap detection

`prerequisite_service.detect_gaps(db, owner_id, target_concept_id)`:

1. Traverse incoming prerequisite edges up to depth 3.
2. For each prerequisite, read BKT/rules mastery and evidence count.
3. Status: `gap` only when evidence ≥ 2 and pKnown < 0.45; `early_signal` when one wrong and no prior evidence; `unverified` when evidence < 2; `secure` when pKnown ≥ 0.7 and evidence ≥ 2.
4. Return an ordered remediation path (foundations first) with the reason and evidence count.
5. Cache nothing; compute from stored evidence.

A single wrong answer never produces `gap`. UI copy distinguishes “early signal — confirm with practice” from “gap — rebuild this first.”

### 9.4 Next-best-action

`GET /api/v1/practice/recommendation` returns:

```json
{
  "action": "diagnostic|read|practice|remediate|challenge|explore",
  "chapterSlug": "cbse-10-math-real-numbers",
  "lessonId": "…",
  "conceptId": "cbse-10-math--hcf-and-lcm",
  "title": "Practise HCF and LCM",
  "reason": "Two recent attempts show a developing understanding.",
  "confidence": "medium",
  "evidenceCount": 2
}
```

Priority: no diagnostic → diagnostic; gap → remediate prerequisite; developing concept → practice; secure → challenge; no enrollment → explore. If evidence is insufficient, the action is `diagnostic` or `explore`, never a fabricated weak spot.

### 9.5 Rewards

XP:

- Attempt submitted: +10 (once per attempt).
- Correct answer: +5 bonus.
- Resource completed: +20 (once per resource).
- Diagnostic completed: +40 (once per session).
- Daily goal met: +30 (once per IST day).

Coins:

- Correct answer: +1.
- Badge award: +10.

Levels: `[0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]`; beyond 3200, each level costs an additional 1000 XP. Level 1 starts at 0.

Streaks: IST calendar days. Same day does not increment; next day increments; a gap resets to 1. `streak_longest` only grows. No streak loss warnings, no freeze purchases.

Badges (seed catalog):

| Code | Title | Criteria |
|---|---|---|
| `first_step` | First Step | First graded attempt |
| `sharp_shooter` | Sharp Shooter | 5 correct answers in a row |
| `chapter_climber` | Chapter Climber | Complete all 5 resources in a chapter |
| `comeback` | Comeback | Correct after 3 consecutive wrong answers |
| `streak_3` | Three-Day Trail | 3-day streak |
| `streak_7` | Seven-Day Summit | 7-day streak |
| `diagnostic_explorer` | Diagnostic Explorer | Complete a diagnostic |
| `formula_friend` | Formula Friend | Complete a formula sheet and score ≥ 80% on its practice set |

All awards are idempotent via `(owner_id, idempotency_key)` and `(owner_id, badge_id)`.

---

## 10. AI architecture

### 10.1 Provider abstraction

`app/core/ai_provider.py` becomes provider-aware:

- `LLM_PROVIDER`: `groq`, `openai_compatible`, `lmstudio`.
- `LLM_BASE_URL`: default `http://127.0.0.1:1234/v1`; Groq `https://api.groq.com/openai/v1`.
- `LLM_MODEL`: default `openai/gpt-oss-120b` when provider is Groq; `google/gemma-4-e4b` locally.
- `LLM_API_KEY`: optional; fall back to `GROQ_API_KEY` when provider is Groq.
- `LLM_TIMEOUT_SECONDS` (default 60), `LLM_MAX_RETRIES` (default 2), `LLM_MAX_OUTPUT_TOKENS` (default 1200).
- `EMBEDDING_PROVIDER`: `lmstudio`, `openai`, or `none`.
- `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION=768`.
- `AI_DAILY_MESSAGE_LIMIT` (default 30).
- `BKT_MODE` (`shadow` default), `BKT_ACTIVE_MIN_EVIDENCE=3`.

The provider sends `Authorization: Bearer <key>` when configured. Retries are bounded and only for transient failures. Health probes chat and, when configured, embeddings. Logs never include headers or keys.

### 10.2 Library retrieval

`library_retrieval.py` scores published resource blocks by:

- token overlap with the question (TF-IDF-ish, stopwords removed),
- heading/title match,
- concept label match,
- chapter filter when supplied,
- resource-kind boost for detailed lessons and formula sheets.

It returns `{pathId, lessonId, title, section, excerpt, score}`. No embeddings are required, so the tutor works on a cold start.

For uploaded documents, keep the existing hybrid retrieval but add an FTS-only fallback when embeddings are unavailable. Do not fail the entire tutor because LM Studio is down.

### 10.3 Prompt contract

System prompt:

- You are ZENITH’s study tutor for Indian Classes 6–10.
- Use the supplied excerpts first. If they do not contain the answer, say so and give a general explanation.
- Show steps, not just the final answer. Ask one checking question at the end when appropriate.
- Never reveal answer keys, hidden test answers, or another student’s data.
- Keep language simple, age-appropriate, and encouraging.
- Cite excerpts with `[1]`, `[2]` matching the citation list.

The service validates that every citation index used exists. If the model cites nothing but excerpts were supplied, append a “Sources used” list. If the model returns unsafe/empty content, return a safe fallback.

### 10.4 Offline tutor

Offline “Ask Zenith” writes to the new Dexie `tutorOutbox` table (same outbox pattern as `doubtOutbox`, with `ownerId`, `threadId`, `question`, `status`, and timestamps). On reconnect, sync answers through the tutor service and cache the answer. The UI labels offline answers as “queued — will answer when connected.” No fake immediate answer.

---

## 11. Offline and PWA

- Dexie schema version 3 adds `libraryResources` (published package cache), `resourceProgress`, and `tutorOutbox`; existing tables and `SetuDeskDB` name stay.
- Cache a library resource explicitly (“Save offline”) or automatically for the current chapter’s next resource.
- Offline attempts queue with `attemptKind` and idempotency key; sync on reconnect, focus/resume, and manual “Sync now.”
- Conflict policy: server wins for grades and mastery; client progress merges by `updated_at`; never duplicate XP.
- Service worker precaches the app shell; runtime cache for fonts and static assets. Do not cache API responses containing personal data.
- Offline banner shows pending counts and last error; no blocking modal.
- Storage quota: show estimated size before download; handle `QuotaExceededError` with a clear message and cleanup action.
- Account switching clears or scopes cached rows by `ownerId` (already enforced).

---

## 12. Security, privacy, rights

- All student data endpoints require a valid Supabase JWT. Public library reads are the only anonymous endpoints.
- Library content is original; `sourceRefs: []` and `rights: original` are recorded. Uploaded documents remain private to the owner, their classroom teacher, or a catalogue/sample source as today.
- No service-role key in the frontend. No secrets in logs, error messages, or API responses.
- Rate limits: AI daily quota per user; auth handled by Supabase. The public catalogue is read-only and the hosting platform provides the network-level limit; no application-level per-IP limiter is added in this scope.
- Input validation: Pydantic models, max lengths, enum checks, UUID parsing, answer payload size limits.
- Output safety: redact answer keys, sanitize prose, escape HTML in the frontend, no `dangerouslySetInnerHTML` for AI content.
- CORS: explicit production origins; no wildcard with credentials.
- Security headers on the API and static host.
- Data retention: tutor threads deletable by the student; diagnostics expire after 24 hours; no AI training on student data (provider policy documented).
- RLS remains enabled with default deny; the API is the enforcement boundary. Add an operations note and authorization tests.

---

## 13. Deployment

### 13.1 Backend

- `backend/requirements.txt`: pinned runtime dependencies (FastAPI, uvicorn/gunicorn, SQLAlchemy, Alembic, psycopg, pydantic-settings, httpx, python-jose/cryptography, pdfplumber, PyMuPDF, python-docx, python-pptx, pytesseract, Pillow, pgvector, etc.).
- `backend/requirements-dev.txt`: pytest, pytest-asyncio, sympy, ruff (optional).
- `backend/Dockerfile`: Python 3.12-slim, tesseract-ocr, non-root user, `alembic upgrade head && uvicorn` entrypoint.
- `render.yaml`: backend Docker web service, health check `/api/v1/health`, env vars declared with `sync: false` for secrets.
- `backend/.env.production.example`: placeholders only.

### 13.2 Frontend

- `VITE_API_BASE_URL` respected by `api.ts` and `syncManager.ts`; fallback `/api/v1` for same-origin/proxy.
- `frontend/public/_redirects`: `/* /index.html 200`.
- `frontend/public/_headers`: CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, cache rules for hashed assets.
- `frontend/.env.production.example`.
- Optional `render.yaml` static site or Cloudflare Pages build settings documented.

### 13.3 Verification

- `scripts/smoke_production.ps1`: check `/api/v1/health`, `/api/v1/library/catalogue`, one chapter, one resource (auth required), CORS preflight, and frontend HTML title.
- Local production run: `docker build`, `docker run` with a disposable DB, `npm run build`, `npm run preview`, Playwright smoke.
- Actual cloud deployment is **pending credentials/account access** and must not be claimed until the smoke script passes against the live URL.

---

## 14. Testing and acceptance criteria

### 14.1 Backend

- New unit tests for BKT, rewards, prerequisites, diagnostics, validator, library access, tutor, AI provider config.
- New integration tests for catalogue/chapter/resource/enrollment/progress/diagnostics/rewards/tutor using the disposable PostgreSQL.
- Authorization tests: personal paths, documents, attempts, diagnostics, rewards, tutor threads are not readable across users; library is readable by any authenticated user; draft library is not.
- Idempotency tests: seed twice, submit same attempt sync key twice, complete diagnostic twice, claim daily reward twice.
- Content tests: 4 chapters, 20 resources, ≥60 questions, DAG acyclic, every MCQ answer in options, no placeholders, math answer verification.
- Existing 197 tests continue to pass after updating expectations for branding and library access.

### 14.2 Frontend

- `npm run build` passes with route-level code splitting; main entry chunk ≤ 220 kB gzip.
- Playwright: onboarding, explore filters, chapter open, reader, practice attempt, feedback, XP toast, map, achievements, Ask Zenith (mocked/real), offline save/sync, teacher dashboard, branding assertions.
- Accessibility: axe-core on Home, Explore, Chapter, Practice, Map, Achievements; no serious/critical violations.
- Manual: keyboard-only navigation, reduced motion, high contrast, 360 px width, slow 3G.

### 14.3 Product acceptance

1. A brand-new student can sign up, complete onboarding, open CBSE 10 Maths, read a lesson, answer a practice question, see evidence-based feedback, and earn XP without uploading anything.
2. The library shows exactly 4 published chapters and 20 published resources, all labelled “Founding library · CBSE Class 10 Mathematics.”
3. An empty subject shows an honest empty state and a working content request.
4. A wrong answer produces “early signal” language, not a false mastery verdict; a second wrong or a diagnostic confirms a gap.
5. BKT is computed in shadow mode for every new attempt; the UI does not claim BKT superiority.
6. XP, coins, streaks, and badges are idempotent and derived from stored events.
7. Ask Zenith cites library sections and refuses to invent citations; it works when embeddings are unavailable.
8. Teacher classroom flows still work and show readable concept labels.
9. Offline reading and queued attempts sync without duplicates.
10. No user-facing “SETU” remains; internal compatibility identifiers are documented.
11. No secret appears in the frontend bundle, logs, or API responses.
12. Deployment configs exist and a local production smoke test passes; live deployment is explicitly marked pending.

---

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Content authoring takes longer than expected | Lock 4 chapters × 5 resources; author in chapter-sized tasks; validator catches gaps early |
| Math errors in original content | Every answer key verified; `verify_library_math.py`; worked examples re-solved; review checklist |
| BKT destabilises existing mastery UI | Shadow mode default; rules remain primary; compare script; feature flag |
| Library paths break existing owner checks | Central `library_access.py`; authorization tests; no remediation injection for library |
| Cold-start AI/LM Studio down | Groq production config; FTS-only retrieval fallback; honest degraded state |
| Large frontend bundle | Route-level `React.lazy`, shared primitives, no heavy chart/DAG dependency |
| Empty library for non-CBSE users | Honest empty state + content request; no fabricated shelves |
| Offline sync duplicates XP | Server idempotency keys; client outbox keys; tests |
| Deployment blocked on credentials | Configs + local Docker smoke; explicit pending status in STATUS_REPORT |
| Scope creep | Non-goals list; cut line is extra chapters/subjects, not core loop quality |

---

## 16. Delivery phases

1. **Safety and brand** — backup, baseline tests, design gate, tokens/logo/metadata, shell.
2. **Data foundation** — migration 009, models, library validator/seed/publish.
3. **Founding library** — concepts/DAG + 4 chapters × 5 resources + diagnostic banks.
4. **Learning engine** — library APIs, access policy, BKT, prerequisites, rewards, diagnostics.
5. **AI** — provider abstraction, retrieval, tutor, quota.
6. **Student experience** — onboarding, Home, Explore, Chapter, Reader, My Learning, Practice, Map, Achievements, Profile, Ask.
7. **Preserved flows** — Sources, teacher dashboard, offline.
8. **Production readiness** — Docker, Render/Cloudflare configs, smoke script, docs.
9. **Verification** — full test suite, Playwright, accessibility, performance, security review, final reviewer.

**Cut line if time runs short:** additional chapters/subjects, voice/image doubts, parent accounts, leaderboards. The core loop, library quality, and honest evidence must not be cut.
