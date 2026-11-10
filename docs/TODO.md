# ZENITH to-do list (working plan)

Legend: [me] I do it | [you] you do it | [both] needs a decision or approval. Tick items as they finish; STATUS_REPORT.md records results.

## Honest scope for "deployed today"

A full production platform with 12 teacher-reviewed chapters is weeks of content work. What can genuinely ship today, polished, is a **vertical slice**:
sign-up -> pick class -> Learn library -> lesson reader with checks -> adaptive practice -> concept gaps -> teacher class view -> weekly league, all on real database records, deployed on free Vercel + Supabase + Groq. Chapters appear only after a teacher (you) approves them in the review screen; everything else shows "Coming soon".

## A. Unblockers (needed first)

- [ ] A1 [you] Authorise Vercel access for team `leeladhar2804-2489s-projects` (my Vercel connector returned 403).
- [ ] A2 [you] Confirm I may push branch `zenith/transform` to GitHub `origin` (Vercel deploys from Git).
- [ ] A3 [you] In the Vercel project settings add env vars from `backend/.env.production.example` (values never in chat).
- [ ] A4 [both] Approve the production database reset (backup first, then drop legacy document tables, apply new migrations). Existing 8 users are test data.

## B. Visual research done properly (B1 done with screenshots; B2 partial; B3 mockup at docs/design/v2/index.html awaiting your approval)

- [x] B1 [me] Inspect Canvas Classes in a real rendered browser (screenshots of home, class page, chapter, lesson, tools) for layout, rhythm and components. View only; no copying of content, text or assets.
- [~] B2 [me] Same for 2-3 more reference sites that render in a browser (Khan Academy India, Brilliant, Duolingo) using screenshots instead of text scraping.
- [~] B3 [me] New design v2: responsive **desktop + mobile**, component kit, animation set. Show 4 key screens rendered; you approve before the full build.

## C. Foundation (backend)

- [ ] C1 [me] Migrations: boards, curriculum versions, chapters, lessons and versions (draft -> approved -> published), items, concepts, prerequisite edges, evidence log, concept states, classrooms, league tables.
- [ ] C2 [me] Content importer + validator (schema, SymPy answers, prerequisite graph). Load existing 10 chapters as drafts.
- [ ] C3 [me] Review API + screen: teacher approves; DB forbids publishing without approval.
- [ ] C4 [me] Evidence API with server-side answer checking; BKT per concept; item selection; prerequisite gap probes; next-best-action with stored reasons.
- [ ] C5 [me] Teacher API: class overview, concept heatmap, misconceptions, recommendations, assignments.
- [ ] C6 [me] League/quests/streaks (classroom-scoped, opt-out).
- [ ] C7 [me] Tutor: grounded in published lessons, Hindi/Telugu replies labelled AI-translated, graceful when Groq is down or rate-limited.
- [ ] C8 [me] Security pass: RLS deny-all kept, fix `rls_auto_enable()` exposure, rate limits, input validation.
- [ ] C9 [me] Tests written alongside each item (pytest on disposable Postgres).

## D. Frontend rebuild (lightweight, animated)

- [ ] D1 [me] App shell: bottom nav on phone, sidebar on desktop, route-level lazy loading, view transitions, skeletons.
- [ ] D2 [me] Component kit (Button, Card, Chip, Sheet, Tabs, Progress path, Toast, etc.) with spring/ease motion; reduced-motion respected.
- [ ] D3 [me] Screens: Landing/sign-in, Onboarding, Today, Learn (class -> subject -> chapter), Lesson reader, Practice, Climb, Ask, Settings.
- [ ] D4 [me] Teacher screens: Class, Concepts heatmap, Student, Assign, Review queue.
- [ ] D5 [me] Interactive widgets: number line, fraction/balance model, step-reveal worked examples.
- [ ] D6 [me] Offline: download chapter, queue answers, idempotent sync.
- [ ] D7 [me] Performance: initial JS <= 170 kB gzip, Lighthouse mobile >= 90, fonts subset.

## E. Content (the long pole)

- [ ] E1 [me] Upgrade the existing Class 6-10 chapter drafts: more questions, misconception-tagged options, diagrams as SVG, worked examples, proper notation.
- [ ] E2 [both] You review and approve in the review screen (target for today: as many chapters as you can approve; rest stays "Coming soon").
- [ ] E3 [you] Confirm curriculum year per class (NCERT 2025-26 editions) so chapter numbers are right.

## F. Deploy and verify

- [ ] F1 [me] Vercel config: static frontend + FastAPI function, one origin, security headers, cache rules.
- [ ] F2 [me] Supabase: Auth URLs, migrations, keep-alive, weekly backup proposal.
- [ ] F3 [me] Post-deploy smoke test script (sign-up -> lesson -> answer -> teacher sees evidence).
- [ ] F4 [me] STATUS_REPORT, README, runbook.

## Order of work

B (research + design approval) -> C1-C4 + D1-D3 (core learning loop) -> E1-E2 -> C5-C6 + D4 -> C7 -> F -> D6 as time allows.
Anything not finished today is shown as "Coming soon" or hidden, never faked.
