# ZENITH remaining work (updated 2026-11-11)

Working method: check what already exists before writing; reuse; finish every caller, test and fixture; one small test for new logic; end each report with what was skipped or not checked. Lessons: write, dry-run, independent review, then publish (see CONTENT_AUTHORING.md).

## A. Waiting on the owner (nothing I can do alone)
1. Run `backend/sql/realtime_class_chat.sql` in the Supabase SQL editor (live chat updates; chat polls every 7 s until then).
2. Giphy API key into Vercel as `GIPHY_API_KEY` (GIF search is off without it).
3. Vercel env: confirm `B2_KEY_ID`, `B2_APP_KEY`, `B2_BUCKET` (chat files), `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (live pings), `SUPABASE_SECRET_KEY`; rotate the Backblaze key.
4. Retire the earlier India layer: `python -m app.cli asset retire f830578b-71fa-4a6e-bc13-47e356638d65 <reviewer-email> "superseded"`.
5. Decide whether to install Ponytail (always-on Node hooks; `/plugin marketplace add DietrichGebert/ponytail` then `/plugin install ponytail@ponytail`, typed in an interactive Claude Code prompt).
6. Update AGENTS.md rule 6 if lessons may be published by delegated approval (current practice: gates + independent review + audit row under the owner's reviewer account).
7. Authorise the Vercel connector (team access) if deployments should be inspected directly.
8. Three real accounts (student, student, teacher) for the live 1v1 / chat test later.

## B. Verify what already shipped (never seen in a browser or on production while signed in)
1. DONE 2026-11-11: automated render sweep of all 39 published lessons (clipped labels, stray `^`, leaked entities, placeholders). Fixed: real superscripts for `^` powers everywhere (new `ui/powers`), two clipped figure labels. Still to do by eye: simulations and label_diagram item at 360 px.
2. Production smoke test with real student and teacher accounts: sign in, Home, Learn, Practice, Explore, Progress (Gap Map with real evidence), My Classes, chat, announcements, leave and rejoin.
3. Chat with three users at once (needs A1): reactions, threads, polls, pins, search, blocking, muting, reporting, files, typing, presence, unread.
4. DONE: chat, files and GIF search require guardian or school consent for students (tests added).
5. DONE: open-report count on the teacher's class card, class page and Reports tab. (Email or push alerts not built.)
6. Accessibility pass (keyboard, focus, screen reader labels) on chat, classes, atlas, new simulations.
7. Performance on slow 3G and a low-end Android: lesson page with simulation, class chat, atlas with overlays.
8. Twenty-one older lessons have duplicate re-imported versions queued (identical content): clean up the reviewer queue.
9. Remove the stale `planned` references and re-run the full backend suite (360+ tests) and the frontend suite after the next batch.

## C. Classroom (original request, section 2)
1. DONE 2026-11-11: Files tab per class. Teacher shares PDF, pictures, Word, Excel (no macros) or PowerPoint up to 4 MB, or https links; students open files through ten-minute signed links; private B2 under `classfiles/`; migration 007. Not yet tried against real B2 from a browser (tests use a fake store).
2. Assignment creation from the class page; due-date reminders; student "upcoming activities" on Home.
3. Discussion topics separate from the main chat (one channel per topic) if wanted.
4. Moderation tools: teacher can unmute from the class page, view mute list, export a report.
5. Realtime 1v1 quiz (later, after everything else): Elo matchmaking from Zenith ratings, questions from the verified bank, server-side answer checking, anti-cheat timers, Supabase Realtime, tested with three accounts.

## D. Live Books and content (sections 3 and 6)
1. DONE 2026-11-11: Sound published for Class 9 (waves, wavelength, v = f x wavelength, echo, reverberation, ultrasound, sonar); the stale Class 8 chapter is archived. Reviewer suggestions still open for a later pass: time period and f = 1/T, timbre and intensity, speed of sound versus temperature and medium, SONAR full form and ultrasound uses, structure of the ear.
2. Maths coverage, Classes 6 to 10: list every chapter of the current NCERT books (Class 6 and 7 and 8 Ganita Prakash, Class 9 Ganita Manjari, Class 10 Mathematics) and write the missing lessons in priority order. Done so far: HCF and LCM, fractions, integers, equations, exponents, triangles, squares, solids, coordinates, quadratics.
3. Science coverage, Classes 6 to 10 (Curiosity 6 to 8, Exploration 9, Science 10): biology (nutrition, respiration, reproduction, life processes, heredity, ecosystems), chemistry (matter, atoms, metals and non-metals, carbon compounds), physics (light mirrors and lenses, magnetic effects, energy, work and power). Done so far: heat, acids, pressure, magnets, circuits, cells, separation, pH, motion, laws of motion, balancing equations, light refraction, Ohm's law, gravity.
4. Social Science (needs a new subject): history, geography (maps, rivers, mountains, climate), civics, economics; Classes 6 to 10.
5. Language of explanation: Hindi and Telugu versions of the lessons (product decision: hi, te, en), using the existing language field.
6. Lesson depth items from the original request still missing everywhere: "further practice" and "related concepts" links, a revision-notes page per chapter, chapter recap pages, prerequisites shown before a lesson.
7. Board-pattern practice: a tag for item pattern (MCQ, assertion-reason, case-based, short and long answer), a Practice mode filtered by pattern, chapter tests built from them, sets modelled on the board paper structure. Never reproduce previous-year papers (copyright); write new questions in the same pattern.
8. Source licensing for images: use Wikimedia Commons (now configured), NASA, OpenStax with attribution stored in B2; diagrams stay original SVG otherwise.
9. Reviewer notes still open: Class 7 solving-equations placement; chapter numbers from secondary sources; loose misconception tags; the `^` notation renderer.

## E. Simulations (section 4)
1. Built: projectile motion, refraction, circuits, 3D solids. Not yet used in a lesson beyond the four published.
2. Still to build: friction and energy, mirrors and lenses (ray diagrams), atoms and molecules (3D), mixtures and separation, chemical reactions, cells and plant structures (3D), organs and body systems, geometry transformations and 3D visualisation (Math Visual Lab).
3. Each needs: correct model as a tested pure function, controls, live readout, guided challenge, reset and step mode, no-WebGL and low-memory fallback, and a lesson that uses it.

## F. Maps and Data Stories (section 5)
1. Map lessons: Indian states quiz, rivers, mountains and plateaus, using `overlays:` (layers are imported and approved).
2. Data Stories lessons for the approved-pending World Bank datasets (population, life expectancy); approve the datasets, then write the lessons with a task and a quiz.
3. More datasets (data.gov.in, World Bank indicators, NASA) with licence and attribution checks.
4. Timelines for history (needs sourced events).

## G. Learning engine and existing features (sections 1 and 5)
1. Gap Map: check the populated view with real evidence, and that "Practise this" and "Test this topic" links land correctly.
2. Mistake Detective, Today and missions, topic tests and adaptive recommendations: end-to-end check with real accounts.
3. Knowledge Map: show mastery colours, prerequisite edges, root causes from the gap engine.
4. Offline learning: audit Dexie queue (lessons, attempts, doubts), idempotent sync on reconnect, focus and manual sync; add tests.
5. Scores and XP: re-verify live updates in every quiz mode (practice, test, revision, boss quiz, lessons).

## H. Platform
1. Scheduled backups (GitHub Actions secrets) and a restore drill.
2. Rate limits and abuse checks on chat upload and GIF search; security headers review.
3. Documentation: update DEPLOY.md, README, status report after each wave.


## Update 2026-11-11 (evening)
DONE since the list above:
- Data Stories: two Maths lessons on the approved World Bank datasets (Class 8 population line graph, Class 9 life expectancy), numbers re-checked against the rows by an independent reviewer. Both datasets approved.
- Social Science subject added (icon, colour with checked contrast). Two Class 7 geography lessons with the interactive map layers (mountains, plateaus and the Thar Desert; rivers of India), facts reviewed; moved from Class 9 to Class 7 after the reviewer found the current book places them there. Placement rests on third-party summaries of the new NCERT books: a reviewer should confirm against ncert.nic.in.
- Practice has a question-type filter (multiple choice, assertion and reason, numerical). Case-based questions cannot be told apart reliably from their wording, so they are not offered as a filter yet (needs an explicit tag on the item, which means re-importing items).
- Offline sync: fixed a bug where a queue of more than 100 saved answers could never be sent (the server accepts 100 per request); added "answers waiting" with a Send now button on the Offline page; tested.
- Knowledge Map: tapping a weak topic shows why and which earlier topic is the root cause.
- Gap Map seen populated in a browser (range chart, root cause, repair order, links).
- Live now: 44 lessons, 35 chapters, 638 questions, three subjects.

STILL TO DO (new or unchanged):
1. More Social Science: history, civics, economics, more geography (climate, soils, agriculture); needs timelines and sourced events for history.
2. Doubts offline (tutor questions saved while offline and sent later): not built, needs a UX decision.
3. Case-based and assertion-reason tagging on items (explicit field) so every pattern can be filtered.
4. Upgrade 14 of the older lessons' reviewer notes; more Maths and Science chapters (see section D); Hindi and Telugu versions once the English set is stable.
5. Remaining simulations (section E), 1v1 quiz (section C5), production smoke test with real accounts (section B2), chat with three accounts (needs A1).

## Source-to-lesson pipeline (added)
`python -m app.cli source list|import|draft`. Fetch (robots.txt, vetted hosts only) -> licence check on the page -> clean/filter -> pending credited asset -> reviewer approves -> AI-assisted draft (JSON, `ai_assisted`, diagram left as TODO) -> gates -> named review.
- Vetted: NASA, USGS Water Science School, NOAA Ocean Service (US-government public domain; text with its own copyright notice is dropped).
- Refused on purpose (see `textsource.REFUSED`): OpenStax (CC BY-NC-SA and an AI-ingestion ban), NCERT, Wikipedia (share-alike), Khan, CK-12, NROER.
- Proven live: NOAA "What are tides?" imported as pending. The draft step is only tested with a fake model (needs ENABLE_REMOTE_AI=true). Some pages (USGS water cycle) are script-rendered and yield no text.
