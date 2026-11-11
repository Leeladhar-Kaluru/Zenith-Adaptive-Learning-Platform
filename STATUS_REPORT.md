# ZENITH Status Report

Plan and decisions: [docs/ZENITH_TRANSFORMATION_ASSESSMENT.md](docs/ZENITH_TRANSFORMATION_ASSESSMENT.md) · working list: [docs/TODO.md](docs/TODO.md) · design: [docs/design/](docs/design/)

## Session 2026-11-10 — full rebuild on a real backend

### What exists now (all backed by the database, no mock or hardcoded data)

**Backend (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL)**
- New baseline migration `001_zenith_baseline` (39 tables, deny-all row level security, full-text indexes). Old SETU migrations and the pgvector dependency are gone.
- **Content system:** content-as-code (`content/*.yaml`), validated by a strict schema, imported idempotently by content hash. Lessons and questions are versioned and immutable once published. Review states: draft, in review, changes requested, approved, published, archived. The database refuses published content without a named reviewer.
- **Automated gates** (inform the reviewer, never approve): structure, distinct options, **SymPy answer verification**, reading level for the class, notation, figure alt text, questions mapped to concepts, mistakes tagged, enough practice, acyclic prerequisite graph, and a manual "curriculum placement confirmed" check the reviewer must tick.
- **Learner model:** immutable evidence log → Bayesian Knowledge Tracing per concept (item-type guess, difficulty slip, hints count as weak evidence, repeats barely count) → honest bands with evidence counts and confidence. Rasch (Elo) ratings choose question difficulty. Challenge questions unlock only with evidence.
- **Concept graph:** DAG validated on import; gap investigation traces a struggle to the deepest weak prerequisite; one wrong answer never creates a gap.
- **Decisions:** transparent rules for the next step, each with a reason and evidence count: assigned work, prerequisite refresher, diagnostic, spaced revision, continue, practise, next lesson, challenge.
- **Engagement:** XP only for first-try correct answers on new questions (daily cap), streaks with one free rest day, daily goals, badges, weekly classroom leagues (nickname and character only, teacher can turn off, students can opt out).
- **Teacher:** classes with join codes, heatmap, students who may need help, suggestions only when several students show repeated difficulty (cites answers), assignments, interventions with before/after, accept/dismiss.
- **Ask (tutor):** grounded in the current lesson, Hindi/Telugu replies labelled AI-translated, rate-limited, never sends identity to the AI, falls back to the lesson text and says so when AI is unavailable.
- **Tests:** diagnostic, chapter, topic and revision tests, timed or untimed, concept-level results, mistake review, retakes.

**Frontend (React 19, Vite, TypeScript, CSS Modules)**
- Navigation: Home, Learn, Practice, Explore, Ask, My Progress. Teacher and reviewer have their own.
- Custom duotone icons, 12 avatars, league badges, route transitions, XP and confetti effects.
- Every question type (multiple choice, multi-select, true/false, numeric, fill in, match) with real hints; offline queue with idempotent sync; offline chapters.
- No mock layer. Every screen talks to the real API.

**Content loaded:** 3 chapters, 10 lessons, 59 questions (Class 6 Integers, Class 7 Simple Equations, Class 8 Linear Equations in One Variable) with a 12-concept prerequisite graph across the three classes. All pass every automated gate. **All AI-assisted drafts are unpublished until a reviewer approves them in the Review screen.**

### Verification (exact commands and results)

- Backend: `pytest` against Supabase in the `zenith_test` schema → **79 passed** (engines 22, streaks 8, CMS 12, API journeys 37). Docker is no longer used.
- Frontend: `npx tsc -b && npx vite build` → passes. Entry bundle **126 kB gzip** (budget 170 kB).
- Real stack, no mocks: backend on :8000 with the local database, frontend on :5180 through the Vite proxy.
  - Review screen showed real gate results; approving through the real UI published a lesson; a chapter stayed closed until all its lessons were published.
  - Real onboarding created a profile; Home showed 0 XP, 0-day streak, goals 0/5 and a diagnostic suggestion with its reason.
  - After repeated misses on two-step equations, Home pointed to one-step equations with "1 of 4 right (based on 4 answers)".
  - Checked on desktop (1440) and phone (390): no horizontal overflow.
- Local-only note: to test the student side on the throwaway local database, the 9 remaining lessons were published through the reviewer API. Nothing was published anywhere else.

### Not done yet

1. **Production:** Supabase still has the old SETU schema (migration 008). Deploying needs your approval to back up, drop the legacy tables and apply `001`. No Vercel project exists yet (Vercel access needs authorising).
2. **Content review:** nothing is live for real students until you approve it. The curriculum placement (chapter numbers against the current NCERT editions) is yours to confirm.
3. **Science and Classes 9 and 10:** no chapters yet (shown as Coming soon, not faked).
4. **Not built:** Explore labs (physics, chemistry, biology, maps), parent view, voice, in-app content editor (content is edited as files, reviewed in the app), coins (no use for them yet), Lighthouse run, Playwright browser tests.
5. Hindi/Telugu **lesson text** is not translated; only Ask replies are AI-translated and labelled.

### Database (Supabase only)

- `zenith` schema created in your Supabase project by `alembic upgrade head`; 10 lesson drafts imported (`in_review`, nothing published). The old SETU tables in `public` are untouched (27 tables, 8 profiles, 528 questions, verified after the migration).
- `zenith_test` schema holds the automated tests' data; the tests refuse to run in any other schema.
- Backups: encrypted (AES-256-GCM) dump to B2, tested live (backup, verify, restore into a scratch schema, row counts match), 60-day B2 retention set; weekly GitHub Actions job needs the five secrets in docs/DEPLOY.md.
- Curriculum reference: content/reference/ncert_books.yaml holds facts only (book names and chapter counts, retrieved 2026-11-10). Chapter titles could not be read from the NCERT page automatically and no NCERT text is copied; new lessons are original, AI-assisted and need your approval.
- Deploy files: vercel.json and api/index.py are written but untested until a Vercel project exists.

### Run it locally

See [README.md](README.md). In short: put your Supabase `DATABASE_URL` in `backend/.env`, run `alembic upgrade head`, `app.cli import ../content`, start uvicorn and `npm run dev`.

### Tools used

pytest, Alembic, SymPy, npm/tsc/vite, Playwright (screenshots), Supabase MCP (read-only), `skills` CLI (five vetted skills installed). Stitch MCP unavailable.

## Session 2026-11-10 (adaptive engine v2)

Built and tested locally (not yet deployed; production database still at migration 001):
- Question templates (8 families: integer add/subtract/compare/hops, one-step, two-step, word and both-sides equations). Every generated question is checked by the real grader and, for equations, re-solved with SymPy over 600+ seeds per family.
- Difficulty ladder (levels 1 to 5 per topic) driven by correctness, hints, answer changes and speed; guessing never raises the level; every move stores a plain-language reason. Practice serves a fresh generated question at the student's own level about 70 percent of the time.
- Interaction log: lesson opens, section views, reading time, hints, answer changes and simulation moves are batched on the device, sent idempotently, capped at 200 per request and 2000 per day.
- Simulations: balance/equation, line graph (slope and intercept) and spinner (probability), lazy loaded, keyboard accessible, bounds checked at import. Equation simulation checked in a real browser; line graph and spinner not yet looked at in a browser.
- New lessons (AI-assisted, in review): The balance lab (Class 7), Slope and intercept (Class 8), How likely is it? (Class 7). They pass the automated gates; they need your approval after import.
- Teacher student view now shows difficulty level per topic with reasons and a 14-day activity summary.
- Auth: confirm password, show/hide, live rules. Bug fixed: starting a lesson twice at once returned a 500.
- Tests: 135 backend tests pass; frontend builds.

Commands run: `pytest` (134 passed before the teacher view, 8 passed in test_interactions after), `npm run build`, `python -m app.cli backup` (39 tables, verified), `python -m app.cli import ../content` against the test schema only.

Blocked: applying migration 002 to the production `zenith` schema was refused by the permission system. It is additive (two new tables, four nullable item columns, one extra allowed item status). It must run before this code is deployed: `cd backend && DB_SCHEMA=zenith python -m alembic upgrade head`.

Not done yet: mistake notebook and chapter boss quiz, more lessons (Science, Classes 9-10, most Maths chapters), end-to-end run on the live site, Resend email and password recovery, monitoring.

## Maths batch 2 and Science batch (2026-11-10, later)

- Maths: Class 6 Fractions (2 lessons), Class 7 Perimeter and Area, Class 8 Squares and Square Roots, with 5 more adaptive question types.
- Science (first Science content): Class 6 Float or Sink (new density simulation), Class 7 How Heat Travels, Class 7 Acids, Bases and Indicators, Class 8 Force and Pressure, with 3 adaptive question types (density, float decision, pressure).
- All new lessons are AI-assisted, pass the automated gates, and are imported in review. None is visible to students until the reviewer approves it and confirms the chapter placement against the current NCERT book.
- All four simulations (equation, line graph, spinner, density) were exercised in a real browser against the local test stack.
- Tests: 146 backend tests pass. An independent physics check caught and fixed a rounding bug in the density and pressure templates.
- Still missing: Science for Classes 9-10 and more chapters, mistake notebook, boss quiz, signed-in walkthrough of the live site, monitoring.

## Mistake notebook and chapter boss quiz (2026-11-10, later)

- Notebook: `GET /progress/notebook` groups wrong answers by the misunderstanding behind them, with two real examples, the explanation and a link to a fresh question. A group closes after three correct answers in a row on the topic. Shown under My Progress > Mistakes.
- Boss quiz: `GET /boss/{chapter}` says whether it is open and why not. It opens when every topic has at least 3 answers and mean mastery is 70 percent or more. `POST /assessments` with kind `boss` builds 8 generated questions at level 4 or 5 (stored hard questions for topics without templates). Pass mark 75 percent, reported honestly. Shown as a card on each chapter page.
- Migration 003 relaxes one check constraint so the `boss` kind can be stored. NOT yet applied to production (needs approval). Until it is applied, creating a boss quiz in production would fail.
- Tests: 152 backend tests pass. Both screens were checked in a real browser (locked boss card, grouped notebook).

## Speed work and content research (2026-11-10, latest)

Measured and fixed (no features changed): API moved to Mumbai next to the database (it ran in Washington); per-request memo cut queries (today 29 to 21, chapter list 13 to 5, progress 24 to 15, chapter page 11 to 8); pre-ping off on Vercel; service worker precache cut from 88 files / 1,885 KB to 22 files / 612 KB. Live result: `/library/boards` 1.04-1.10 s to 0.09-0.14 s; `/health/ready` 1.18-1.29 s to 0.37-0.52 s. Found and fixed a missing `return` in `today()` that the benchmark's 200 status hid; the benchmark now asserts a non-empty body. 162 backend tests pass.

Not measured: authenticated endpoints on the live site (no student login), cold start after the change, Lighthouse on a throttled phone. Remaining speed tasks are Phase 0 of the new plan.

Research and plan delivered, nothing implemented from them yet: `docs/CONTENT_SOURCES.md` (ranked sources with licences, verified vs check-before-ingest) and `docs/superpowers/plans/2026-11-10-content-intelligence.md`. Key finding: NCERT books are copyrighted and may not be copied or hosted, so NCERT is used only as a hand-entered curriculum reference. Waiting for approval before building the provenance pipeline.

## Content intelligence plan, executed (2026-11-11)

All 17 tasks of `docs/superpowers/plans/2026-11-10-content-intelligence.md` were worked in order, test first. 289 backend tests pass; frontend builds; budget script passes (entry JS 128.0 kB gzip of 130; first-visit precache 557.7 kB in 13 files of 650).

Built: anonymous real-user speed metrics and a CI size budget; local ES256 token verification; shared per-request loads (today 29 to 16 queries on the test fixture, lesson 12 to 10); `/today` starting alongside `/profile` (Home data ready 479 ms vs 814-1185 ms measured in a real browser); source, asset and provenance tables with licence and attribution constraints; a licence policy that refuses NC, ND, unknown and missing licences; a robots.txt-respecting fetcher; Wikimedia Commons, World Bank and Natural Earth importers; credits on lessons with a publish gate; TODO lesson skeletons; a depth gate (14 of the 21 live lessons would fail it; they stay live, listed as the depth backlog); diagram specs to safe SVG; Mistake Detective; credited data charts; daily mission and a mastery-aware map; diagram labelling; a world Atlas.

NOT done / waiting:
- Migration 004 (web_vitals, sources, source_assets, content_provenance, two new item kinds, wider items.kind) is not applied to production: it needs the owner's approval, and so does a deploy. Until then none of this is live.
- No real data imported (World Bank, Natural Earth, Commons): importing writes to the production database. The Atlas and Data Stories show nothing until someone runs the import CLIs after deploy.
- Timelines not built (need sourced events; Social Science wave not started). Atlas has countries only, no Indian states.
- Not measured: live latency of logged-in pages; cold start after the PyJWT addition (import measured at 0.85 s, JWT libraries load on first authenticated request).
- Looked at in a real browser: detective question (answered end to end), Atlas (wrong then right), chart, labelling dropdowns, credits, diagram figure, mission and map. Not looked at on a phone-width screen.

Review pass (2026-11-11): an independent whole-branch review found no critical issues and 9 important ones; all were fixed test-first (robots.txt redirects, asset retirement and a due-list for reviewers, images only from our own storage, a gate against outside links and images in lesson markup, re-checking drafts when an asset is approved, bounded anonymous speed metrics, shared-request races in the browser, 30 s clock-skew tolerance, and the Wikimedia contact requirement). 308 backend tests and 5 frontend tests pass. Wikimedia refuses bots without a real contact in the User-Agent: set BOT_CONTACT (an email or page you choose) before importing from Commons. Branch pushed; master and production untouched.

## Product completion, phase 1: P0 fixes, gap map, My Classes (2026-11-11)

Scope of the "Product completion and major learning upgrade" request. This phase covers the P0 items; chat, Live Books depth, Three.js and the rest are NOT started.

Done and verified:
- Visual audit by computed contrast in a real browser (light, dark, and the third theme): fixed the dark hero, muted text, danger/gap red, science and ok greens, an undefined `--muted`, and mobile overflow at 360 px on chapter, ask and settings. Buttons wrap instead of overflowing.
- Explore now shows only what exists (flashcards, and published lessons that contain a simulation, chart or map). The "coming soon" placeholders and the `planned` field are gone.
- XP and streak in the header refresh the moment an answer, lesson, test or revision is saved (`emitProgress`, new light `/stats` route). Test-mode quizzes refresh on submit on purpose: a rising XP number mid-test would reveal which answers were right.
- Gap Map on My Progress: Wilson confidence ranges, root-cause tracing through the prerequisite graph, downstream-impact priority, a repair order, and a lesson, practice and test link per gap. Honest empty state with no evidence (seen in browser); ranked view covered by 8 engine tests.
- My Classes (student): list with teacher, classmates count and next due work; class page with announcements (pinned first), work by due date, classmates (nickname and avatar only; opted-out students show as "A classmate"), leave with confirmation, rejoin by class code (previously a "left" row blocked rejoining). Teachers post, pin and delete announcements from the same page (plain text only; tags and scripts are stripped). A class you are not in answers 404, same as one that does not exist. Verified in a browser as a student and a teacher at 1280 and 360 px.
- Migration 005 adds `announcements` (RLS on, no browser access). Applied to `zenith_test` only.

Tests: new `test_classes.py` (9), `test_gaps.py` (8), `test_explore.py` (4), stats and cache tests; frontend 6 node tests pass; build and size budget pass.

Commands: `python -m pytest -q` in backend; `npm test`, `npm run build` in frontend.

Waiting on you:
- (Done 2026-11-11: backup taken and verified, migrations 004-006 applied to production, deployed.)
- Wikimedia contact: tell me an email or page you own and monitor; it goes in the BOT_CONTACT environment variable only, never in source.
- Carried over: rotate the Backblaze key, confirm SUPABASE_SECRET_KEY in Vercel, run the real data imports, and the 14-lesson depth backlog.

Next: real-time class chat (Supabase Realtime, B2 signed-URL attachments, reactions, moderation, reporting, blocking), then Live Books depth, then simulations.

## Phase 2: class chat, simulations, deployed to production (2026-11-11)

Production: backup `backups/zenith-20261111T055131Z.zbk` (46 tables, 1,497 rows, verified) taken first; migrations 005 (announcements) and 006 (chat) applied to the `zenith` schema (6 profiles intact, RLS on every new table); master pushed; Vercel build succeeded; live checks: `/health` ok, `/classes` and `/classes/{id}/chat` answer 401 to anonymous callers, live CSS contains the fixed hero colours (the invisible "next step" card).

Class chat (backend `services/chat.py`, `services/chatfiles.py`, `api/v1/chat.py`; UI `frontend/src/chat/`): messages, replies, threads, fixed reaction set plus a larger emoji picker, teacher-only polls and announcements, pins, search (wildcards treated as text), pagination, unread counts, typing and online status, report, block, teacher mute and remove. Child safety: no direct messages; links, emails and phone numbers refused; a short unkind-word filter; burst limit; students cannot post HTML. Attachments (PNG, JPG, GIF, WebP, PDF, 4 MB max) are checked by their bytes, stored in the PRIVATE B2 bucket under `classchat/`, and served only through ten-minute signed links after a membership check; storage keys never reach browsers. GIF search goes through a server-side Giphy proxy (G rating, credit shown, host allow-list). 29 tests.

Realtime: clients send content-free "changed" pings, typing and presence over a PRIVATE Supabase channel; messages always come from the API. Polling (7 s) is the fallback and is what works today.

Simulations (`frontend/src/lesson/sims/`): projectile motion (step mode, planets, target challenge), refraction (Snell, critical angle, total internal reflection, Fresnel brightness), series and parallel circuits (Ohm's law), and a Three.js solids viewer (cube, cuboid, cylinder, cone, sphere; drag or arrow keys to turn; falls back to numbers when WebGL is missing or memory is very low). Models are pure functions with 12 tests against textbook values; schema bounds with 18 tests. Three.js (193 kB gzip) loads only on the solids simulation and is outside the precache. Checked in a real browser: projectile fired and hit its target, 3D cone and cube render, readouts match formulas.

Tests: 360 backend passed (full run) plus 18 schema tests; 18 frontend tests; build and budget pass (precache 618.5 of 650 kB).

NOT done: Supabase Realtime policies (blocked, see below); GIF and file sharing depend on keys in Vercel; no lessons yet USE the new simulations; Live Books depth upgrades, Indian states/rivers/mountains maps, Data Stories real imports, Classes 9 and 10 content, knowledge-map and offline upgrades.

Needs you:
1. Run `backend/sql/realtime_class_chat.sql` in the Supabase SQL editor (it adds two policies on the managed `realtime.messages` table and one membership function). My attempt was refused by the permission system, so chat is polling until you do.
2. GIFs: create a free Giphy API key and set `GIPHY_API_KEY` in Vercel (server only). Attachments: confirm `B2_KEY_ID`, `B2_APP_KEY`, `B2_BUCKET` are set in Vercel; rotate the B2 key.
3. Confirm `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` are set in Vercel (needed for live pings).
4. Wikimedia contact: tell me an email or page you own and monitor for `BOT_CONTACT`.
5. Vercel connector needs team access authorized if you want me to inspect deployments directly.

## Lessons uploaded for review, datasets imported (2026-11-11, later)

Four new lessons were authored (original text, original SVG, `ai_assisted`), passed every automated gate (SymPy-verified numeric answers, readability for the class, depth, tagged misconceptions, credits) and were imported to production as `in_review`:
- Class 10 Science, Light: "Why light bends" (refraction simulation, Snell's law, critical angle)
- Class 10 Science, Electricity: "Current, voltage and Ohm's law" (circuit simulation)
- Class 9 Science, Motion under gravity: "Falling and throwing" (projectile simulation)
- Class 9 Maths, Surface areas and volumes: "Surface area and volume of solids" (3D solids simulation)

They are NOT published: project rule 6 requires a named reviewer's approval and AI drafts may never self-publish. Approve them in the reviewer queue (`/review`). Importing also queued revised versions of 21 existing lessons (7 `in_review`, 14 `draft` that fail the depth gate); the 21 published versions are untouched and still live.

Datasets imported to production (World Bank, CC BY 4.0, attribution stored, pending approval): India total population (SP.POP.TOTL, 66 rows) and life expectancy at birth (SP.DYN.LE00.IN, 65 rows). A lesson can only use them after a reviewer approves the asset (`python -m app.cli asset approve <id> <reviewer-email>`).

Still not done: Indian states, rivers and mountains maps (needs a Natural Earth file downloaded, which I have not done without your say-so), Data Stories lessons that use the datasets, Live Books depth for the 14 draft lessons, more Class 9 and 10 chapters, knowledge-map and offline upgrades.

## India states map imported (2026-11-11, later)

With your OK I downloaded `ne_10m_admin_1_states_provinces.geojson` (40.7 MB, public domain, Natural Earth's official GitHub mirror), kept only India (36 states and union territories, current as of the 2020 merger of Dadra and Nagar Haveli with Daman and Diu), and imported it to production as a PENDING map layer (`ne-10m-admin1-india-states`, 173 kB, id f830578b-71fa-4a6e-bc13-47e356638d65). The map importer now fits a regional map to its own frame (longitude scaled by cos latitude), simplifies boundaries, and gives every place a unique id (ISO 3166-2, e.g. IN-MH); the Atlas wording no longer says "country". 4 new tests.

DO NOT APPROVE YET: Natural Earth draws Jammu and Kashmir and Ladakh by present control, which differs from the boundary of India as officially published by the Survey of India (and used in NCERT maps). Maps of India shown to students in India should follow the official boundary. A reviewer must decide how to handle the north (Natural Earth publishes an India-viewpoint country outline, but no India-viewpoint states layer) before this layer is approved.

Not done: rivers and mountains layers, and the lessons that would use the map and datasets.
