# ZENITH goal and remaining work (13 Nov 2026)

**Goal.** An adaptive learning platform for Classes 6 to 10 that works offline first: a student installs it as an app, saves chapters, studies and practises with no internet, and the platform adapts to them from real evidence, with complete and honest analysis of how they are doing. Content is original or licensed, checked by gates and approved by a named reviewer. Every number on screen comes from the database or deterministic model code.

## Done (live unless noted)
- Adaptive core: BKT mastery per topic, Rasch ratings, levels 1 to 5, gap engine with root cause, revision schedule, practice that targets the student's level, adaptive check with early stop and interval, forgetting-curve fading topics, optional confidence tap with calibration .
- Offline: installable PWA with install prompt and iPhone instructions , saved chapters, offline answers and tutor questions with idempotent sync on reconnect, focus and manual, saved dashboard snapshot, offline practice from saved lessons , suggested chapters to save next .
- Social: classes, chat with Realtime pings, files, announcements, ranked 1v1 Arena with quiz Elo and battle history, notifications bell.
- Content: 80+ published lessons across Maths, Science, Social Science, English; simulations (circuits, refraction, projectile, density, solids, friction, optics, transformations, line graph, equation, spinner); Hindi and Telugu chapters waiting for a native reviewer.
- Pipeline: requests, source discovery from vetted open-licence sources, evaluator scorecard, infographics, reviewer screen, background worker with retries, stale-lock recovery, heartbeat and health screen, running on a free Render service that wakes on real triggers.

## Needs your decision
1. DONE on the free tier: `zenith-worker` runs on Render (wakes on real triggers, sleeps when idle). Move to a paid always-on worker later by switching the service type and start command.
2. Set `ENABLE_REMOTE_AI` and the Groq key where drafting runs, or drafts are never made.
3. A native Hindi reader and a native Telugu reader to approve those chapters.
4. Whether to move the API to Render later (not recommended until Vercel limits bite).

## To do, in order
1. DONE: migrations 010 and 011 are live; the Render worker is verified end to end.
2. Define curriculum topics (concepts) for every class and subject that has none, so the pipeline has something to search for; remove the Vercel cron fallback after a week of stable worker runs.
3. Content waves through the pipeline and author agents: every class has Maths, Science, Social Science and English chapters first (coverage table shows the gaps: Classes 6, 8, 9, 10 are thin), then Hindi and Telugu with reviewers.
4. Remaining simulations: atoms and molecules, mixtures and separation, chemical reactions, cells, organs, Maths visual lab.
5. Adaptive depth: use calibration to pick confidence-building questions; misconception repair sets from repeated wrong options; target 70 to 85 % success shown to the student; offline model snapshot so the next offline question adapts from the last known profile.
6. Offline depth: background download of recommended packs on Wi-Fi, storage meter and clean-up, offline Arena is not possible (needs the server) and says so.
7. Real two-browser Realtime test of chat and Arena with real sign-ins; 360 px review of the newer pages; accessibility pass.
8. Reviewer tooling: one-click export of an approved draft into a lesson version (today it is copied into the content folder by hand).
