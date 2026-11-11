# ZENITH next phase: plan (11 Nov 2026)

Seven asks, in the order they will be built. Every number on screen comes from the database or the model code. Nothing is mocked, seeded or invented.

## Rules that shape the design (from AGENTS.md, kept on purpose)
- Vercel serverless: no process that runs by itself. "Live in the background" is done with **Vercel Cron** (scheduled calls to a protected endpoint), on-demand triggers when a student opens a class or subject with thin coverage, and short polling / Supabase Realtime for the screen.
- Nothing reaches students until a lesson version is `published` with automated checks passing and a **named reviewer's approval**. AI-assisted drafts are always labelled `ai_assisted` and never publish themselves. So the pipeline fills a **review queue** quickly; it does not push unreviewed text to children. The owner's standing delegation (publish when every check passes) still applies to the reviewer account.
- Only licence-clean sources (public domain, CC BY, CC0). Share-alike, non-commercial, NCERT and similar are refused (see `textsource.REFUSED`). Images only from Wikimedia Commons with licence and attribution recorded.
- Competitive features stay inside a class, can be opted out of, and show only nickname and avatar.
- Learner modelling is deterministic and every recommendation stores its evidence.

## 1. Practice: subject filter
A Subject selector on Practice (from the subjects the API returns for the student's board and grade), combined with the existing question-type filter. The server filters concepts by subject and grade; no subject list is hardcoded.

## 2. Ranked 1v1 arena
- Why it was invisible: it lived only inside a class tab. Now a top-level **Arena** page (sidebar and bottom bar) shows the student's classes, a Play button per class, the class table and the student's rating. A student in no class sees a clear "join a class to play" explanation, because ranked play is classroom-scoped.
- Real time: match state is pushed with a Supabase Realtime ping per match (same pattern as chat), with polling as the fallback. Opponent progress updates as answers arrive.
- **Battle history** on the Profile: every finished match with opponent nickname, result, score, rating change, date, and a per-question review.

## 3. Profile as a live dashboard
One page that answers "how am I doing?" from real data: mastery by subject and chapter, accuracy and speed trends (14/30 days), streak and daily activity, weak topics with the evidence, XP and level, quiz rating and battles, revision due, offline status (packs saved, answers waiting to sync). Refreshes on every answer (the existing progress event), on focus and on reconnect, and polls gently while visible.

## 4. Adaptive and offline first
- The analysis works offline: the last dashboard snapshot is stored in Dexie with a "last updated" stamp; answers made offline are included in a clearly marked "pending" count and merged on sync.
- Offline packs: save a chapter (already built) plus **auto-suggest** the packs the student will need next (from the recommendation engine), shown with size.
- Service worker keeps the shell and API reads for lessons usable offline.

## 5 and 6. Content pipeline and coverage
Stages: **discover** (vetted source adapters and sitemaps) -> **fetch** (polite, robots.txt, rate limited) -> **licence check** -> **extract and filter** -> **evaluate** -> **draft** (ai_assisted, structured JSON, simple words) -> **gates** -> **review queue** -> **publish** -> **notify**.
- New tables: `ingest_jobs` (what was asked, by whom or by cron, status, counts, errors), `coverage_requests` (class, grade, subject, topic), `notifications` (per user, kind, link, read).
- **Evaluator**: a scorecard stored with every draft: licence verdict, readability against the class, relevance to the concept, duplicate check against existing lessons, fact-sourcing (every sentence traceable to the source), question quality (one correct option, distractors distinct), and diagram/alt-text presence. Below threshold = rejected with reasons.
- **Coverage view**: for every grade and subject, how many chapters and lessons are published, in review, or missing. The student UI never shows an empty subject without a real explanation and a "request lessons" button, which creates a coverage request.
- **Runner**: a protected cron endpoint processes a small batch per call (serverless-safe): picks the highest-demand coverage request, runs the stages, stops before the time limit and resumes next call.
- **Infographics**: original SVG built deterministically from structured fields the draft supplies (process flow, comparison, timeline, labelled parts), so they are original and accessible. **Images**: Wikimedia Commons importer with licence and credit shown under the image.
- **Notifications**: a bell with unread count; "new lessons for your class", "your quiz opponent is ready", "revision due". Delivered by Realtime ping with polling fallback; push notifications through the PWA where the browser allows.
- Reviewer experience: queue sorted by demand, one screen with the evaluator scorecard, source, gates and diff.

Known limit, stated openly: the web has little open-licence school content for Indian classes in Hindi/Telugu or for civics and history. Those subjects will fill more slowly and will show their real coverage rather than hidden gaps.

## 7. Adaptive engine (research and build)
See `docs/ADAPTIVE_RESEARCH.md`. Built first: adaptive test with early stopping, forgetting-curve mastery decay and spaced review, response-time and hint-aware evidence weighting, misconception-targeted remediation sets, and an explanation of every adaptation shown to the student.

## Build order
1. Practice subject filter, Arena page, battle history (small, visible).
2. Notifications table and bell (needed by 3 and 5).
3. Profile dashboard and offline snapshot.
4. Pipeline tables, evaluator, coverage view, cron runner, reviewer queue.
5. Adaptive engine features, then content waves with the pipeline and authors.
Each step: tests, browser check, backup before any migration, deploy, verify, update STATUS_REPORT.md.
