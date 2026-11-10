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
