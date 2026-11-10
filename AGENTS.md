# ZENITH persistent project rules

1. The visible product name is ZENITH, everywhere: UI text, logos, browser titles, PWA manifests, onboarding, emails, API root responses and AI tutor persona. Never show a version suffix. "SETU" may remain only in internal identifiers that are costly to rename (git repository, Supabase project/bucket names) and must never be user-visible.
2. No hardcoded production users, progress, subjects, languages, boards, resource counts, lessons, quizzes, classroom memberships, leaderboard entries or fabricated analytics. Real database records and API responses only.
3. Keep production flows board/grade/subject/language/student/classroom agnostic. Fixtures and deterministic fallbacks belong strictly in isolated test environments.
4. Frontend: React 19 + Vite + TypeScript + CSS Modules with design tokens as CSS custom properties; no Tailwind or shadcn. Performance budget: mobile-first, fast on low-end Android over 3G; route-level code splitting; heavy libraries (e.g. KaTeX) load only where used.
5. Backend: FastAPI modular monolith, deployable as Vercel serverless functions (no long-running background loops in the request process). Supabase PostgreSQL + Auth (+ Storage only for content media). PostgreSQL full-text search for tutor grounding. No document upload, OCR, embeddings or pgvector.
6. Curriculum content is typed and versioned in the database. Nothing reaches students unless its lesson version is `published`, and `published` requires automated validation to pass AND a named teacher/reviewer approval. AI-assisted drafts are always labelled `ai_assisted` and can never self-publish.
7. Learner modelling is deterministic and auditable: answer verification is never done by an LLM; mastery comes only from the evidence log via versioned model code (BKT/Elo); every recommendation stores the evidence behind it.
8. Offline lessons, attempts and doubts live in IndexedDB (Dexie); reconnect sync is idempotent and triggered by reconnect, focus/resume or manual action.
9. Never output/log/commit secrets. Never expose secret keys in the browser. Never send student names, emails or IDs to AI providers.
10. Child privacy: collect the minimum data (display name, grade, board, language, age band); guardian/school consent before storing learning evidence; competitive features are classroom-scoped, opt-out-able and never show other students' personal data publicly.
11. Supabase changes: backup and inventory first, drop only application-owned objects, preserve managed schemas (`auth`, `storage`, `vault`, `realtime`, `extensions`); destructive production steps need explicit user approval. Record verification in `context/RESET_REPORT.md`.
12. Use Stitch MCP for design when it is available; otherwise design in code against the token system and verify with browser screenshots at 360, 768 and 1280 px.
13. Update `STATUS_REPORT.md` each session with changes, exact commands/results, tools, blockers and next steps.
14. No NCERT or third-party text/images are rehosted; all lesson text and diagrams are original or properly licensed with recorded attribution.
