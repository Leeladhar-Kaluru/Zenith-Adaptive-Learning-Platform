# ZENITH Content Intelligence and Product Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give ZENITH a licence-safe content pipeline and a small set of genuinely distinctive learning features, on a platform that loads fast on a low-end phone over 3G.

**Architecture:** Every external asset enters through one provenance gate (source, licence, attribution, hash, reviewer) before it can appear in a lesson. Lessons stay original, authored as YAML and gated like today. New features are typed, parameterised widgets (as the four simulations already are) fed by small derived datasets stored with their attribution.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Supabase), React 19 + Vite + TypeScript + CSS Modules, Dexie, SymPy. No new heavy runtime dependencies on the API (serverless size and cold start).

**Spec:** `docs/CONTENT_SOURCES.md` (sources and licences), `docs/AUDIT_AND_PLAN.md` (earlier audit), the request of 2026-11-10 (content intelligence, unique features, speed).

## Global Constraints

- Visible product name is ZENITH; no version suffix in UI text.
- No hardcoded users, progress, subjects, counts, lessons or fabricated analytics; fixtures only in tests.
- Never copy NCERT or any third-party text, exercises or figures. Only open-licensed assets are imported, each with recorded provenance and visible attribution.
- Excluded licences: any NC (non-commercial) or ND (no-derivatives) licence. Share-alike assets are shown only as separate credited items, never merged into lesson prose.
- Respect robots.txt, API terms and rate limits; no scraping where terms forbid it. API or bulk download first.
- Nothing reaches students unless its lesson version is `published` (validation passes and a named reviewer approves). AI-assisted drafts are labelled `ai_assisted` and cannot self-publish.
- Answer verification is never done by an LLM; mastery comes only from the evidence log.
- No student names, emails or ids go to AI providers.
- Frontend: CSS Modules and design tokens, mobile first, route-level code splitting, heavy libraries load only where used. Budget: entry JS under 130 kB gzip; app-shell precache under 650 kB.
- Backend: modular monolith deployable as Vercel serverless functions in `bom1` next to the database; no long-running loops.
- Production data is never deleted; migrations are additive; every production migration needs the owner's approval and a verified backup first.
- Tests run only against `zenith_test`.

## Review Focus

- An asset with a missing or unrecognised licence must be rejected at import, never imported "for now".
- A licence that looks open but is NC or ND (for example CC BY-NC-SA) must be rejected even when the source page calls it "open".
- A fetch must obey robots.txt and back off on HTTP 429; a disallowed URL must never be requested.
- A lesson that uses an asset without attribution text must fail the publish gate, and the credit must appear on the student page.
- A dataset that is later removed or re-licensed upstream must not silently stay live: provenance records its retrieval date and a re-check date.

---

## What exists today (audit of the repository)

Already built and working, so not duplicated:
- Adaptive core: BKT per topic, Elo item difficulty, 1 to 5 difficulty ladder with stored reasons, 16 deterministic question families (integers, equations, area and perimeter, squares, fractions, density, pressure), interaction log, mistake notebook grouped by misconception, chapter boss quiz.
- Four interactive simulations (equation balance, line graph, spinner, density) with schema bounds, tracking and challenge goals.
- Content-as-code: YAML to importer to gates to reviewer approval; 12 published chapters (Maths and Science, Classes 6 to 8), 21 published lessons, 157 stored questions.
- Teacher workspace, leagues, quests, streaks, tutor with honest degraded mode, offline queue (Dexie), PWA.
- Prerequisite graph with a concept map page and gap investigation.
- Backups (encrypted to B2 with 60-day retention), CI, Vercel deploy in `bom1`.

Gaps this plan addresses: no provenance or licence tracking, no asset library, no diagram generator, no data-driven features (atlas, data stories, timelines), content volume (about 12 of roughly 130 NCERT-sized chapters for Classes 6 to 10 Maths and Science), and further speed work (below).

## Speed work already done (measured)

| Measure | Before | After |
|---|---|---|
| API region | Washington (`iad1`) against a Mumbai database | Mumbai (`bom1`), confirmed by `x-vercel-id: bom1::bom1` |
| Live `/library/boards` (one database call) | 1.04 to 1.10 s | 0.09 to 0.14 s |
| Live `/health/ready` | 1.18 to 1.29 s | 0.37 to 0.52 s |
| `/today` queries per request | 29 | 21 |
| Chapter list queries | 13 | 5 |
| Progress overview queries | 24 | 15 |
| Chapter page queries | 11 | 8 |
| Service worker precache on first visit | 88 files, 1,885 KB | 22 files, 612 KB |
| Tests | 152 | 162 passing |

The remaining speed tasks are in Phase 0.

## Unique features: evaluation and priority

| # | Feature | Learning value | Complexity | Data needed | Technology | Priority |
|---|---|---|---|---|---|---|
| 1 | **Science Explorer** (own accurate simulations, credited PhET links for others) | High: students change variables and see laws emerge | Medium each, reuses the simulation frame | None for own sims | React widgets on the existing `SimFrame`; physics in plain TypeScript | **1** (continue: 6 more sims) |
| 2 | **Maths Visual Lab** (fraction bars, area models, number line, graphing, geometry constructions) | High: makes abstract ideas concrete | Medium | None | Same frame, SVG/canvas | **1** |
| 3 | **Mistake Detective** (find the wrong step in a worked solution; practice from your own misconceptions) | Very high: misconception repair is the core of adaptivity; we already tag every wrong option | Low to medium | Existing misconception tags | New question kind `find_error` graded by index; generated from templates | **1** |
| 4 | **Adaptive daily missions** (a 10 minute plan: one revision, one new step, one challenge, with reasons) | High: habit and focus | Low: policy and quests exist | Evidence log | Extend `home.today` | **2** |
| 5 | **Real-World Data Stories** (Indian rainfall, crop yields, literacy; plot, then question) | High: relevance and data literacy | Medium | Small derived datasets from data.gov.in and World Bank, with attribution | Chart widget, JSON snapshots in our bucket | **2** |
| 6 | **Knowledge Galaxy** (visual prerequisite map with your mastery) | Medium to high: shows the path | Low: concept map page exists | Existing graph | Upgrade the existing map page | **2** |
| 7 | **Diagram labelling and flashcard quizzes** | High for Science | Low to medium | Our own SVG diagrams | New item kind `label_diagram` graded by region ids | **2** |
| 8 | **Interactive Atlas** (India and world: states, rivers, plateaus; click to answer) | High for Social Science and Geography | Medium | Natural Earth, Wikidata, census data | TopoJSON + SVG, no tile server | **3** |
| 9 | **Historical timelines** | Medium | Low | Hand-curated events with sources | Timeline widget | **3** |
| 10 | **Offline packs** (chapter plus its generated-question seeds) | High for low connectivity | Medium: lesson packs exist | Existing | Extend Dexie packs; generated items by seed need server, so pack stored questions plus a seed list that the server resolves on reconnect | **2** |

Extra ideas chosen for standing out:
- **Teach-back:** the student explains a step in a few words; ZENITH shows a checklist of the key ideas that should appear, and the student ticks what they included. No AI grading; the checklist is authored. It builds explanation skill without trusting a model to mark it.
- **Beat yesterday's you:** a private streak against your own accuracy and speed, no public comparison (child privacy rule).
- **Hindi and Telugu term chips:** every key term in a lesson has a tap-to-reveal translation in the student's language, authored and reviewed, not machine output.
- **Read aloud:** the browser's built-in speech for low-reading-level students, offline, no data sent.
- **Exam readiness radar:** per chapter, which topics are secure, shaky or untested, with the evidence count.

## Curriculum expansion roadmap (Maths and Science first)

Chapter counts from `content/reference/ncert_books.yaml`: Maths 67 (Class 6: 10, 7: 15, 8: 14, 9: 14, 10: 14), Science 63 (12, 12, 13, 13, 13). Today 12 chapters exist, so about 9 percent. Each chapter is 3 to 4 lessons.

| Wave | Scope | Chapters | Gate |
|---|---|---|---|
| 1 | Maths Classes 6 to 8, remaining core chapters | 25 | reviewer approves 5 per batch |
| 2 | Science Classes 6 to 8 | 30 | same |
| 3 | Maths and Science Class 9 | 22 | same |
| 4 | Maths and Science Class 10 | 24 | same |
| 5 | Social Science (history, geography with the Atlas, civics, economics) Classes 6 to 10 | about 45 | after Atlas and Timelines |
| 6 | English and Hindi language skills | later | after the above |

At the review pace seen so far, plan about 5 chapters per review sitting; waves 1 to 4 are roughly 20 sittings. Authoring is the bottleneck, so the pipeline below exists to make each chapter faster to draft and faster to verify, not to skip review.

---

## File Structure

- `backend/app/models/sources.py` (new): `Source`, `SourceAsset`, `ContentProvenance`.
- `backend/alembic/versions/004_provenance.py` (new, additive).
- `backend/app/ingest/policy.py`, `fetch.py`, `commons.py`, `datasets.py` (new package): licence policy, polite fetcher, per-source adapters.
- `backend/app/cms/gates.py`, `schema.py` (modify): `sources` block and attribution gate.
- `backend/app/cms/draft.py` (new): outline-to-draft helper that always sets `origin: ai_assisted`.
- `backend/app/services/diagrams.py` (new): diagram spec to SVG.
- `backend/app/api/v1/datasets.py` (new): read-only dataset and asset endpoints.
- `frontend/src/lesson/viz/*` (new): chart, atlas, timeline widgets, `find_error` and `label_diagram` question UIs.
- `frontend/src/lesson/Credits.tsx` (new): attribution footer.
- `content/sources/*.yaml` (new): hand-reviewed source and asset records.

---

## Phase 0: Speed (remaining), 1 to 2 days

### Task 1: Measure real users, then enforce a budget

**Files:** Create `frontend/src/lib/vitals.ts`, `backend/app/api/v1/vitals.py`, `.github/workflows/perf.yml`; Test `backend/tests/test_vitals.py`.

**Interfaces:** Produces `POST /api/v1/vitals` body `{name: "LCP"|"INP"|"CLS"|"TTFB", value: number, route: string}`, stored without any user identifier; `GET /api/v1/vitals/summary` (reviewer only) returns p75 per route and metric.

- [ ] **Step 1:** Write `test_vitals_accepts_valid_metric_and_rejects_unknown_name`, `test_vitals_summary_is_reviewer_only`, `test_vitals_stores_no_user_id`.
- [ ] **Step 2:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/test_vitals.py -v`; Expected FAIL.
- [ ] **Step 3:** Implement `record(db, name, value, route)` and `summary(db)`; table `web_vitals(name, value, route, at)` in migration 004. Client uses the browser's own PerformanceObserver, no library.
- [ ] **Step 4:** Run tests; Expected PASS. Add a CI job that builds the frontend and fails if entry JS gzip exceeds 130 kB or precache exceeds 650 kB.
- [ ] **Step 5:** Commit `perf: field metrics and a size budget`.

### Task 2: Verify tokens locally instead of calling Supabase on cold instances

**Files:** Modify `backend/app/core/security.py`; Test `backend/tests/test_jwt_local.py`.

**Interfaces:** Produces `verify_jwt_local(token: str) -> dict | None` using the project's published signing keys (JWKS), cached for 1 hour, falling back to the existing network check if keys cannot be fetched.

- [ ] **Step 1:** Write `test_valid_token_verifies_without_network`, `test_expired_and_wrong_signature_are_rejected`, `test_falls_back_to_network_when_keys_unavailable` with a locally generated key pair.
- [ ] **Step 2:** Run; FAIL. **Step 3:** Implement with PyJWT; check the added dependency does not push the function bundle or cold start beyond today's measured import time (0.9 s).
- [ ] **Step 4:** PASS; measure cold start before and after and record in `STATUS_REPORT.md`. **Step 5:** Commit.

### Task 3: Cut remaining query counts on the heaviest pages

**Files:** Modify `backend/app/services/library.py` (lesson payload, 12 queries), `practice.py` (next item, 15), `home.py` (today, 21).

- [ ] **Step 1:** Write `test_query_budget_*` using the statement counter from the benchmark: lesson at most 7, practice next at most 9, today at most 12, chapter page at most 6.
- [ ] **Step 2:** Run; FAIL (current counts above). **Step 3:** Batch the per-concept lookups with the per-request memo, and fold repeated reads. **Step 4:** PASS with the full suite green. **Step 5:** Commit with the new measured counts in the message.

### Task 4: Fewer round trips from the browser

**Files:** Modify `frontend/src/context/AuthContext.tsx`, `frontend/src/api/useApi.ts`, `frontend/src/pages/Home.tsx`.

- [ ] **Step 1:** Record the request waterfall on `/home` with the in-app browser (before).
- [ ] **Step 2:** Start `/today` in parallel with `/profile`, and prefetch the next lesson's payload when the current lesson is 70 percent read; cache GETs for 30 s with stale-while-revalidate.
- [ ] **Step 3:** Record the waterfall after; Expected: one fewer sequential hop on first paint. **Step 4:** Commit with the before and after timings.

## Phase 1: Provenance and licence safety, 3 to 4 days

### Task 5: Provenance schema

**Files:** Create `backend/app/models/sources.py`, extend `004_provenance.py`; Test `backend/tests/test_provenance_models.py`.

**Interfaces:** Produces tables `sources(id, name, homepage, licence_terms_url, api_terms_url, robots_ok, notes)`, `source_assets(id, source_id, external_id, url, kind, licence_id, attribution_text, author, retrieved_at, recheck_at, sha256, bytes, status)` with a check that `licence_id` is not null, and `content_provenance(lesson_version_id, asset_id)`.

- [ ] **Step 1:** Write tests: asset without `licence_id` fails; duplicate `(source_id, external_id)` fails; deleting a source with assets is blocked.
- [ ] **Step 2:** FAIL. **Step 3:** Models and additive migration, row-level security enabled like the other tables. **Step 4:** PASS. **Step 5:** Commit.

### Task 6: Licence policy

**Files:** Create `backend/app/ingest/policy.py`; Test `backend/tests/test_licence_policy.py`.

**Interfaces:** Produces `evaluate(licence_id: str) -> Decision` where `Decision = {allowed: bool, share_alike: bool, reason: str}`. Allowed: `CC0-1.0`, `PDM-1.0`, `CC-BY-4.0`, `CC-BY-3.0`, `GODL-India`, `US-GOV-PD`. Share-alike only: `CC-BY-SA-4.0`, `CC-BY-SA-3.0`, `ODbL-1.0`. Everything else denied, including all `NC` and `ND` and unknown strings.

- [ ] **Step 1:** Write tests for every allowed id, each SA id (allowed with `share_alike=True`), `CC-BY-NC-SA-4.0`, `CC-BY-ND-4.0`, `""`, `"all rights reserved"` and `"free to use"` (all denied with a clear reason).
- [ ] **Step 2:** FAIL. **Step 3:** Implement as a lookup table, case-insensitive, with SPDX-style ids. **Step 4:** PASS. **Step 5:** Commit.

### Task 7: Polite fetcher

**Files:** Create `backend/app/ingest/fetch.py`; Test `backend/tests/test_fetch.py`.

**Interfaces:** Produces `fetch(url: str, *, user_agent: str) -> bytes` that checks `robots.txt` for the host (cached), refuses disallowed paths with `Disallowed`, waits and retries on 429 or 503 using `Retry-After`, enforces 1 request per second per host, and caps response size at 15 MB.

- [ ] **Step 1:** Write tests with a fake transport: disallowed path never requested; 429 with `Retry-After: 2` waits then succeeds; oversize body aborts; second request to the same host waits at least 1 s.
- [ ] **Step 2:** FAIL. **Step 3:** Implement on `httpx` with the standard library `urllib.robotparser`. **Step 4:** PASS. **Step 5:** Commit.

### Task 8: Wikimedia Commons adapter (first source)

**Files:** Create `backend/app/ingest/commons.py`, extend CLI in `backend/app/cli.py`; Test `backend/tests/test_commons.py`.

**Interfaces:** Produces `import_file(db, title: str, actor_id) -> SourceAsset` calling the Commons API for `imageinfo` with `extmetadata`, mapping `LicenseShortName` to a policy id, storing author and credit string, downloading the file via the fetcher, hashing it, and refusing any file whose licence is denied or missing. CLI: `python -m app.cli asset commons "File:Example.jpg"`.

- [ ] **Step 1:** Write tests with a recorded API response: a CC BY image imports with attribution text and sha256; a CC BY-NC file is rejected with the policy reason; a file with no licence metadata is rejected; re-import is idempotent.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit.

### Task 9: Attribution in lessons

**Files:** Modify `backend/app/cms/schema.py` (lesson `sources: list[str]` asset ids), `backend/app/cms/gates.py`, `backend/app/services/library.py`; Create `frontend/src/lesson/Credits.tsx`; Test `backend/tests/test_attribution_gate.py`.

**Interfaces:** Lesson YAML gains `sources: [asset_id, ...]`. Gate "Imported assets are credited": every figure block referencing an asset must list it in `sources`, and every listed asset must exist, be `approved`, and have attribution text. Lesson payload gains `credits: [{text, url, licence}]`.

- [ ] **Step 1:** Write tests: lesson using an unlisted asset fails the gate; listed asset without attribution fails; a valid lesson passes and its payload carries `credits`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement gate, payload field and a "Credits" footer that lists each asset. **Step 4:** PASS plus a browser check. **Step 5:** Commit.

## Phase 2: Content pipeline, 1 week

### Task 10: Outline-to-draft helper

**Files:** Create `backend/app/cms/draft.py`; Test `backend/tests/test_draft.py`.

**Interfaces:** Produces `new_lesson_skeleton(chapter_slug, slug, title, concept_ids) -> dict` that returns a schema-valid YAML-ready dict with every required section present but empty prompts, `origin: ai_assisted`, and a `TODO` marker that makes `validate` fail until each section is filled. Never calls a model by itself.

- [ ] **Step 1:** Write tests: skeleton fails validation until sections are filled; `origin` is `ai_assisted`; published status is impossible from the skeleton.
- [ ] **Step 2:** FAIL. **Step 3:** Implement and add CLI `python -m app.cli new-lesson ...`. **Step 4:** PASS. **Step 5:** Commit.

### Task 11: Depth gate

**Files:** Modify `backend/app/cms/gates.py`; Test extend `backend/tests/test_cms.py`.

**Interfaces:** New hard gate "Lesson has enough depth": at least 2 worked examples or one example with 3 steps, at least one figure or simulation, at least 8 questions with at least 2 per difficulty level, at least 2 tagged misconceptions, and a recap with at least 3 points.

- [ ] **Step 1:** Write tests: a thin lesson fails with a message naming what is missing; a full lesson passes; existing seed lessons still pass or are listed.
- [ ] **Step 2:** FAIL. **Step 3:** Implement; list any existing lessons that now fail rather than hiding them. **Step 4:** PASS. **Step 5:** Commit.

### Task 12: Diagram specs to SVG

**Files:** Create `backend/app/services/diagrams.py`; Test `backend/tests/test_diagrams.py`.

**Interfaces:** Produces `render(spec: dict) -> tuple[str, str]` returning `(svg, alt_text)` for specs of kind `labelled` (shapes, arrows, labels at named anchors), `axes` and `table`. Output is sanitised (no scripts, no external references) and the alt text is generated from the labels.

- [ ] **Step 1:** Write tests: a labelled cell diagram renders every label; script tags and `href` to external hosts are stripped; alt text mentions each label; the same spec renders identically twice.
- [ ] **Step 2:** FAIL. **Step 3:** Implement with plain string building. **Step 4:** PASS. **Step 5:** Commit.

## Phase 3: Features, ordered by value

### Task 13: Mistake Detective

**Files:** Modify `backend/app/cms/schema.py` (item kind `find_error`), `backend/app/engine/grading.py`, `backend/app/engine/templates/*`; Create `frontend/src/lesson/FindError.tsx`; Test `backend/tests/test_find_error.py`.

**Interfaces:** Item kind `find_error`: payload `{steps: [str, ...]}`, answer spec `{wrong_step: int, misconception: code}`; `grade("find_error", spec, {"step": int})`. A template family builds a worked solution from an existing equation or integer template with one step corrupted by a named misconception.

- [ ] **Step 1:** Write tests: choosing the wrong step is correct; any other step is incorrect and reports the misconception; generated instances always contain exactly one corrupted step.
- [ ] **Step 2:** FAIL. **Step 3:** Implement and wire into practice at ladder level 3 and above. **Step 4:** PASS plus a browser check. **Step 5:** Commit.

### Task 14: Data Stories

**Files:** Create `backend/app/ingest/datasets.py`, `backend/app/api/v1/datasets.py`, `content/datasets/*.yaml`, `frontend/src/lesson/viz/Chart.tsx`; Test `backend/tests/test_datasets.py`.

**Interfaces:** `import_dataset(db, spec) -> SourceAsset` stores a small aggregated JSON (at most 200 KB) with `attribution_text`, `dataset_url`, `retrieved_at`; refuses datasets whose licence the policy denies. Lesson block `{kind: widget, widget: data_chart, dataset: asset_id, x: field, y: field, question: item_key}`. `GET /api/v1/datasets/{id}` returns the data and credit.

- [ ] **Step 1:** Write tests: dataset without licence is refused; stored JSON over the size cap is refused; endpoint returns credit with data; a block referencing an unapproved dataset fails the gate.
- [ ] **Step 2:** FAIL. **Step 3:** Implement with World Bank and data.gov.in adapters (API first). **Step 4:** PASS. **Step 5:** Commit. Pilot with one Maths data-handling lesson and one Science climate lesson.

### Task 15: Daily missions and Galaxy upgrade

**Files:** Modify `backend/app/services/home.py`, `frontend/src/pages/Home.tsx`, `frontend/src/pages/ConceptMap.tsx`; Test `backend/tests/test_missions.py`.

**Interfaces:** `GET /api/v1/mission` returns up to 3 items (`revision`, `new`, `challenge`) each with `reason`, `minutes` and `evidenceCount`; total at most 12 minutes; empty list with a reason for a brand new student (diagnostic first). Map nodes get a mastery ring and a "next unlock" highlight.

- [ ] **Step 1:** Write tests for the three slots, the 12 minute cap and the new-student case. **Step 2:** FAIL. **Step 3:** Implement from existing policy and revision schedule. **Step 4:** PASS and a browser check at 360 px. **Step 5:** Commit.

### Task 16: Diagram labelling and flashcards

**Files:** Modify schema, grading and frontend for item kind `label_diagram`; Test `backend/tests/test_label_diagram.py`.

**Interfaces:** `label_diagram` payload `{svg_asset, regions: [id, ...], labels: [str, ...]}`, answer spec `{pairs: {region_id: label}}`, graded like `match`. UI works by tap on mobile (no drag required).

- [ ] **Step 1:** Write tests: all pairs correct passes; partial credit equals correct fraction; labels are shuffled but regions stay fixed. **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit.

### Task 17: Atlas, then Timelines (after Wave 5 planning)

**Files:** Create `content/datasets/natural-earth-*.yaml`, `frontend/src/lesson/viz/Atlas.tsx`, `Timeline.tsx`; Test `backend/tests/test_atlas_data.py`.

- [ ] **Step 1:** Write tests: only Natural Earth and approved Wikidata assets feed the Atlas; each feature set is under 300 KB; no URL points at a public OSM tile server (test scans built assets).
- [ ] **Step 2:** FAIL. **Step 3:** Implement TopoJSON layers (India states, rivers, major plateaus; world countries) and an SVG renderer with tap-to-answer. **Step 4:** PASS. **Step 5:** Commit.

## Phase 4: Content waves

Run waves 1 to 4 from the roadmap. Each wave is repeated batches of 5 chapters:
- [ ] Reviewer reads the NCERT chapter and records the chapter number, a title in our own words and learning outcomes in `content/reference/` (no copied text).
- [ ] `python -m app.cli new-lesson ...` creates skeletons; authors fill them; add simulations or visuals from Phases 3.
- [ ] `validate`, import to production as `in_review`, reviewer approves in `/review`.
- [ ] After each batch: run the full tests, record counts in `STATUS_REPORT.md`.

## Dependencies

Phase 0 is independent and can start immediately. Phase 1 (Tasks 5 to 9) must finish before any external asset appears in a lesson. Task 12 needs Task 9. Task 14 needs Tasks 5 to 7. Task 13 and Task 15 need no external data and can run in parallel with Phase 1. Task 17 needs Tasks 5 and 6. Content waves can run alongside everything, using only original text and our own widgets until Phase 1 completes.

## Self-review

- **Coverage:** sources and licensing (CONTENT_SOURCES.md), pipeline and database (Tasks 5 to 12), features (evaluation table and Tasks 13 to 17), audit (section above), roadmap (waves), speed (measured table and Tasks 1 to 4).
- **Review Focus:** each of the five lines has a test: missing and NC or ND licences (Task 6 and 8), robots and 429 (Task 7), attribution gate (Task 9), re-check date (Task 5 field plus a CLI report in Task 5 step 3).
- **Names:** `Decision`, `evaluate`, `fetch`, `import_file`, `import_dataset`, `render`, `SourceAsset` are used consistently.
- **Honesty:** licence rows marked "check before ingest" in CONTENT_SOURCES.md are not yet confirmed from the source and are re-checked in Task 8 and Task 14 before any import.
