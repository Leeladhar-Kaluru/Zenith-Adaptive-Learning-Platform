# ZENITH Adaptive Engine v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ZENITH adapt to every move a student makes: generated questions that get harder or easier with performance, interactive simulations inside lessons, full interaction tracking feeding the learner model, and much deeper Maths content.

**Architecture:** Deterministic question templates (SymPy solver, seeded parameters, misconception-based distractors) are materialised as ordinary `items` rows (`origin='generated'`) so grading, evidence and BKT/Elo keep working unchanged. A new `interaction_events` log records every student action (dwell, hint open, answer change, simulation parameter change); a deterministic fluency/struggle signal derived from it shifts the difficulty ladder. Simulations are typed, parameterised React widgets declared in lesson YAML.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, SymPy, pytest on Supabase `zenith_test`; React 19 + Vite + TypeScript + CSS Modules (no Tailwind); KaTeX only where used.

**Spec:** `docs/AUDIT_AND_PLAN.md` (sections 4, 5, 6) plus the user's request of 2026-11-10 (simulations, track every move, richer content).

## Global Constraints

- Visible product name is ZENITH; no version suffix in UI text.
- No hardcoded users, progress, analytics or fake data; fixtures only in tests.
- Answer verification is never done by an LLM; mastery comes only from the evidence log via versioned model code (`param_version` stored on every event).
- Every difficulty change stores its reason.
- AI-assisted drafts are labelled `ai_assisted` and cannot self-publish; published needs validation pass plus the named reviewer's approval.
- Child privacy: minimum data; interaction events stay in our database and never go to AI providers.
- Frontend: CSS Modules + design tokens, mobile first, route-level code splitting; heavy libraries load only where used.
- Tests run against `zenith_test` only (`DB_SCHEMA=zenith_test`), never `public` or `zenith`.
- No destructive production steps; legacy `public` tables untouched.
- No NCERT text or images copied; all content original.

## Review Focus

- A student who answers instantly and wrongly (guessing): difficulty must not ratchet up on speed alone.
- A student who answers correctly only with hints: no level-up.
- Template with no valid parameter draw (divide by zero, answer out of range): retry, then fall back to a stored item, never serve a broken question.
- Same seed gives an identical instance; two students can get different instances of one template.
- Offline replay: evidence for a generated item posted after reconnect still resolves its item.
- Interaction flood (slider dragged 500 times): client batches, server caps per request and per day.
- Simulation with extreme values (0, negatives, huge): clamped, no NaN on screen.
- Student with no data: first session gets sensible intro-level questions.

---

## File Structure

- `backend/app/engine/templates/` (new): `base.py`, `maths_integers.py`, `maths_equations.py`, `maths_linear.py`.
- `backend/app/services/generator.py` (new): `materialise`, `next_generated`.
- `backend/app/engine/ladder.py`, `backend/app/engine/signals.py` (new).
- `backend/app/models/learning.py` (modify): `InteractionEvent`, `ConceptLevel`; `backend/alembic/versions/002_adaptive_v2.py` (new).
- `backend/app/services/interactions.py` (new), `backend/app/api/v1/learn.py` (modify).
- `backend/app/services/practice.py`, `evidence.py` (modify).
- `backend/app/cms/schema.py`, `gates.py` (modify), `frontend/src/lesson/sims/*` (new).
- `frontend/src/track/tracker.ts` (new), `frontend/src/pages/Auth.tsx` (modify).
- `content/chapters/*`, `content/concepts/maths.yaml` (modify/create).

---

### Task 1: Auth form hardening

**Files:** Modify `frontend/src/pages/Auth.tsx`, `frontend/src/pages/pages.module.css`; Create `frontend/src/lib/password.ts`. No frontend test runner exists; verify with build and browser.

**Interfaces:** Produces `passwordProblems(pw: string): string[]` (min 8 chars, a letter, a digit; empty array means valid).

- [ ] **Step 1:** Implement `passwordProblems`.
- [ ] **Step 2:** Sign-up mode: "Confirm password" field; show/hide toggle (`aria-pressed`, label "Show password"/"Hide password") on password fields; live problem list; submit blocked unless valid and equal.
- [ ] **Step 3:** Remove the "Check your email to confirm" branch.
- [ ] **Step 4:** `cd frontend && npm run build`; Expected: success; check at 360 px.
- [ ] **Step 5:** Commit `feat(auth): confirm password, show/hide, validation`.

### Task 2: Template engine core

**Files:** Create `backend/app/engine/templates/__init__.py`, `base.py`; Test `backend/tests/test_templates.py`.

**Interfaces:** Produces
- `@dataclass Instance`: `template_id:str, version:int, seed:int, level:int, kind:str, stem:str, payload:dict, answer_spec:dict, explanation:str, hints:list[str], concepts:list[tuple[str,float]], misconceptions:dict[str,str]`.
- `Template` protocol: `id:str; version:int; concept:str; levels:range; make(rng: random.Random, level:int) -> Instance`.
- `register(t)`, `generate(template_id:str, seed:int, level:int) -> Instance` (raises `KeyError`, `ValueError` for bad level, `InvalidInstance` if the instance fails self-check), `templates_for(concept:str) -> list[Template]`.

- [ ] **Step 1:** Tests: `test_same_seed_same_instance`, `test_different_seeds_vary`, `test_unknown_template_raises`, `test_level_out_of_range_raises`, `test_instance_that_fails_self_check_raises` using a test-only template.
- [ ] **Step 2:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/test_templates.py -v`; Expected FAIL.
- [ ] **Step 3:** Implement; `generate` self-checks that `engine.grading` marks the declared correct answer correct and a distractor wrong.
- [ ] **Step 4:** Run; Expected PASS.
- [ ] **Step 5:** Commit `feat(engine): question template core`.

### Task 3: Maths template families

**Files:** Create `maths_integers.py`, `maths_equations.py`, `maths_linear.py`; Test `backend/tests/test_template_families.py`.

**Interfaces:** Consumes Task 2. Concept ids come from `content/concepts/maths.yaml` (read it; use exactly those ids). Templates, each levels 1..5 (level raises magnitude, steps, sign mixing, word wrapper):
- integers: `int_addsub`, `int_hops`, `int_order`, `int_muldiv`.
- equations: `eq_one_step_add`, `eq_one_step_mul`, `eq_two_step`, `eq_both_sides` (level 4-5), `eq_word`.
- linear: `lin_slope_two_points`, `lin_intercept`, `lin_value_at_x`, `lin_equation_from_point_slope`.
Distractors map to named misconceptions already in the concept YAML (sign dropped, wrong inverse operation, change applied to one side).

- [ ] **Step 1:** Tests over seeds 0..199 and levels 1..5: generation succeeds; SymPy-recomputed answer equals `answer_spec`; options distinct; mean operand size at level 5 > level 1; mean step count non-decreasing by level.
- [ ] **Step 2:** Run; FAIL. **Step 3:** Implement (numeric kind `{"value":..,"tolerance":0}`; MCQ with 4 options). **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(engine): maths template families`.

### Task 4: Persistence

**Files:** Modify `backend/app/models/learning.py`, `backend/app/models/curriculum.py`, `backend/app/models/__init__.py`; Create `backend/alembic/versions/002_adaptive_v2.py`; Test `backend/tests/test_models_v2.py`.

**Interfaces:** Produces tables `concept_levels(student_id, concept_id, level 1..5, streak_up, streak_down, reason, updated_at)` PK `(student_id, concept_id)`; `interaction_events(id, student_id, client_event_id, kind, target_type, target_id, value jsonb, ms, occurred_at, received_at)` unique `(student_id, client_event_id)`, index `(student_id, occurred_at)`, kind check in (`lesson_open`,`section_view`,`dwell`,`hint_open`,`answer_change`,`sim_change`,`sim_reset`,`skip`,`tutor_open`); `items.template_id`, `items.template_version`, `items.template_seed`, `items.level` nullable with a unique partial index on `(template_id, template_version, template_seed, level)` where `origin='generated'`. RLS enabled on both new tables.

- [ ] **Step 1:** Tests: duplicate `(student_id, client_event_id)` fails; duplicate generated tuple fails; level 0 or 6 fails.
- [ ] **Step 2:** FAIL. **Step 3:** Models and migration, schema-aware like `001`. **Step 4:** PASS. **Step 5:** Commit `feat(db): concept levels and interaction events`.

### Task 5: Ladder and signals

**Files:** Create `backend/app/engine/ladder.py`, `signals.py`; Test `backend/tests/test_ladder.py`.

**Interfaces:**
- `ladder.step(level:int, streak_up:int, streak_down:int, *, correct:bool, hints_used:int, fluent:bool, struggling:bool, guessing:bool) -> tuple[int,int,int,str]` returns `(level, streak_up, streak_down, reason)`. Up after 2 clean correct in a row, or 1 if `fluent`; down after 2 wrong in a row, or 1 if `struggling`; hinted-correct neither moves the level nor resets the up streak; `guessing` blocks any increase; bounds 1..5; reason is a plain sentence.
- `signals.classify(recent: list[dict], median_ms: float) -> dict` returns `{"fluent":bool,"struggling":bool,"guessing":bool,"reason":str}`: guessing means wrong in under 15 percent of median time; fluent means correct, no hints, under 70 percent of median; struggling means 2 or more hints or 2 or more answer changes or a skip.

- [ ] **Step 1:** Tests: two clean corrects raise; hinted correct does not; two wrongs lower; never outside 1..5; fast wrong never raises; fluent single correct raises; reasons non-empty.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat(engine): difficulty ladder and signals`.

### Task 6: Generator service and practice integration

**Files:** Create `backend/app/services/generator.py`; Modify `practice.py`, `evidence.py`; Test `backend/tests/test_generated_practice.py`.

**Interfaces:**
- `materialise(db: Session, inst: Instance) -> Item` idempotent on the template tuple; sets `origin='generated'`, `status='published'`, `purpose='practice'`; difficulty intro for levels 1-2, standard 3-4, challenge 5; initial `beta` by level; creates `ItemConcept`.
- `next_generated(db: Session, profile: Profile, concept_id: str) -> Item | None`: reads `concept_levels` (default from BKT p, else 1), draws seeds not seen by this student, returns `None` after 5 failed draws so the caller serves a stored item.
- `evidence.record` computes signals from the item's interaction events, calls `ladder.step`, updates `concept_levels`, returns `levelChange: {from, to, reason}` when changed.
- `/practice/next` uses generated items for concepts with templates, stored items otherwise.

- [ ] **Step 1:** Tests: new student gets level 1; two clean corrects then level 2 served; two wrongs lower level and a prerequisite probe is still queued; two students get different seeds; materialise twice gives one row; generation failure falls back to stored item; evidence on a generated item grades server-side.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS including existing `test_api.py`. **Step 5:** Commit `feat(practice): adaptive generated questions`.

### Task 7: Interaction tracking

**Files:** Create `backend/app/services/interactions.py`, `frontend/src/track/tracker.ts`; Modify `backend/app/api/v1/learn.py`, `frontend/src/lesson/Question.tsx`, `frontend/src/pages/Lesson.tsx`, `frontend/src/offline/sync.ts`; Test `backend/tests/test_interactions.py`.

**Interfaces:**
- `POST /interactions/batch` body `{events:[{clientEventId,kind,targetType,targetId,value,ms,occurredAt}]}`; max 200 per request, 2000 per student per day (extra ignored, response reports stored count); idempotent on `clientEventId`; needs the same consent as evidence.
- `tracker.track(kind:string, targetType:string, targetId:string, value?:unknown, ms?:number): void` batches in memory, flushes every 5 s, on page hide and on reconnect; unsent events kept in Dexie.
- Lesson reader emits `lesson_open`, `section_view`, `dwell`; `Question` emits `hint_open`, `answer_change`, `skip`.

- [ ] **Step 1:** Tests: stores events; duplicate ids ignored; 201 events returns 422; daily cap; no consent 403; no cross-student reads.
- [ ] **Step 2:** FAIL. **Step 3:** Server then client. **Step 4:** PASS and `npm run build`. **Step 5:** Commit `feat: track every student interaction`.

### Task 8: Simulations

**Files:** Modify `backend/app/cms/schema.py` (widget literal gains `simulation`), `backend/app/cms/gates.py`; Create `frontend/src/lesson/sims/{SimFrame,NumberLineSim,BalanceSim,LineGraphSim,SpinnerSim}.tsx`, `sims.module.css`; Test `backend/tests/test_sim_schema.py`.

**Interfaces:**
- YAML block: `{kind: widget, widget: simulation, sim: number_line|balance|line_graph|spinner, params: {...}, task: "plain-language challenge", goal: {...}}`.
- `SimFrame` props `{title:string, children:ReactNode, onChange:(name:string,value:number)=>void, onReset:()=>void}`: labelled keyboard-accessible sliders with `aria-valuetext`, live readout, challenge strip that checks `goal`, logs `sim_change`/`sim_reset` via `tracker.track` throttled to one event per 400 ms per parameter.
- Sims: number line with hop size and direction; balance with add/remove on both sides; line graph with slope and intercept sliders; spinner/coin with trials showing empirical vs theoretical bars. Values clamped; no NaN.
- Gate: unknown `sim`, params outside declared bounds, or missing `task` fails validation. Sims load with `React.lazy`.

- [ ] **Step 1:** Tests: schema accepts each sim; rejects unknown sim and bad params; gate flags missing `task`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement schema/gate, then components. **Step 4:** PASS, build, browser check at 360/768/1280 with extreme values. **Step 5:** Commit `feat(lesson): interactive simulations`.

### Task 9: Mistake notebook and boss quiz

**Files:** Create `backend/app/services/notebook.py`; Modify `home.py`, `practice.py`; Test `backend/tests/test_notebook.py`.

**Interfaces:** `GET /progress/notebook` returns wrong answers grouped by misconception with explanation, concept and a "try a fresh one" item from the same template; wrong answers create revision cards; "today" plan items carry a `reason` from stored evidence; `POST /assessments` kind `boss` draws generated level 4-5 items across a chapter, locked until mean mastery >= 0.7 (else 409 with the reason).

- [ ] **Step 1:** Tests: grouping; card on wrong; boss locked below 0.7, unlocked at 0.7. **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat: mistake notebook and boss quiz`.

### Task 10: Teacher side

**Files:** Modify `backend/app/services/teacher.py`, `frontend/src/pages/teacher/ClassView.tsx`, `StudentView.tsx`, `Assign.tsx`; Test `backend/tests/test_teacher_v2.py`.

**Interfaces:** Class view adds per-concept level distribution and "struggling now" (shown only when at least 3 students are affected); student view shows interaction summary (time per lesson, hints, simulation use) and level changes with stored reasons; `POST /teacher/assignments` accepts `{classId, mode:"weak_concepts", conceptIds?}` and builds each student's quiz from their own levels.

- [ ] **Step 1:** Tests: 3-student minimum; another teacher's class forbidden; assignment uses each student's own level. **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS and build. **Step 5:** Commit `feat(teacher): signals, timeline, assign by weakness`.

### Task 11: Maths content batch 1

**Files:** Create chapters under `content/chapters/*`; extend `content/concepts/maths.yaml`. Each lesson: explanation, at least 2 worked examples, a figure or simulation, common mistakes tied to misconceptions, recap, at least 8 stored items; template coverage where a family exists.

Topics (our own titles; counts in `content/reference/ncert_books.yaml`): Class 6 whole numbers, fractions, basic geometry, data handling; Class 7 integers, fractions and decimals, deeper simple equations, lines and angles, perimeter and area; Class 8 rational numbers, deeper linear equations, squares and square roots, data and probability.

- [ ] **Step 1:** Write chapters labelled `ai_assisted`. **Step 2:** `cd backend && .venv/Scripts/python.exe -m app.cli validate ../content`; Expected `OK`. **Step 3:** Import to production as `in_review` (never auto-publish). **Step 4:** The reviewer approves in `/review`. **Step 5:** Commit `content: maths batch 1`.

### Task 12: End to end verification

**Files:** Create `backend/tests/test_e2e_adaptation.py`, `docs/E2E_REPORT.md`.

- [ ] **Step 1:** Journey test: sign up (dev auth), onboard, learn; 10 fast correct answers raise a concept to level 4 or above; 6 wrong lower it; reasons stored; the teacher sees the same data.
- [ ] **Step 2:** Run the full suite; Expected all pass. **Step 3:** Deploy; browser walkthrough as student and teacher at 360/768/1280 on the live site; record defects in `docs/E2E_REPORT.md` and fix. **Step 4:** Commit `test: end to end adaptation`.

---

## Self-review

- Coverage: simulations (8), tracking every move (4, 7), adaptation (3, 5, 6), richer content (11), teacher (10), auth (1), extras (9), end to end (12). Science, Classes 9-10 content, Resend recovery and monitoring stay in `docs/AUDIT_AND_PLAN.md` phases 3-5.
- Names consistent across tasks: `Instance`, `Template`, `generate`, `materialise`, `next_generated`, `ladder.step`, `signals.classify`, `concept_levels`, `interaction_events`, `tracker.track`.
