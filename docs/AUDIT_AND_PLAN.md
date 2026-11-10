# ZENITH production audit and implementation plan (2026-11-10)

Evidence: repository code, live Supabase `zenith` schema (read-only queries), live API calls to the deployed site, 85 passing backend tests. Not done: a signed-in browser walkthrough of the live site, Lighthouse, a Groq call from production. Those are marked "not verified".

## 1. Feature status

| Feature | Status | Evidence / gap |
|---|---|---|
| Registration, login, session persistence | Complete (API) | `/auth/signup`, `/auth/login` call Supabase; token kept client side; 2 student accounts exist in production. |
| Logout | Partial | Clears token client side only; no server session revoke. Acceptable, document it. |
| Password-only signup, no email confirmation | Complete | Works against Supabase when confirmation is off. The "check your email" branch is dead code to remove. |
| Confirm password, show/hide, validation | Missing | `Auth.tsx` has one plain password field, no strength rules, no confirm, no toggle. |
| Account recovery (forgot/reset password) | Missing | No endpoint, no page. |
| Student dashboard, navigation | Complete (code) / not verified live | Pages and nav exist; production has zero evidence rows so nothing personal has been exercised. |
| Board > Class > Subject > Chapter > Lesson | Partial | Structure complete. Content: 1 board, 2 subjects, 3 chapters, 10 lessons, all Maths Classes 6-8. Science has no chapters. Classes 9-10 empty. |
| Lesson reader (explain, examples, formulas, recap) | Complete (code) | Six question kinds, KaTeX, hints. |
| Diagrams | Partial | Widget support exists; only a number-line lesson uses one. Most lessons have none. |
| Practice, tests, hints, explanations, mistake review | Complete (code, tested) | `/practice/next`, `/assessments`, `/items/{id}/hint`, `/progress/mistakes`. Limited by a fixed bank of 59 questions. |
| Adaptive learning, real BKT | Complete engine / Partial product | `engine/bkt.py` is true BKT (guess/slip/transit), Elo item difficulty, selector targets success probability. Weak because the pool is tiny: a student sees the same questions within minutes, and "harder" has few items to choose. Production evidence rows = 0 so never exercised live. |
| Dynamic quiz generation | Missing | Selector only chooses from the stored bank. Nothing is generated. This is the main gap you described. |
| Progress and mastery | Complete (code) | concept_states, lesson_progress, revision cards. |
| AI tutor (Groq) | Complete (backend) | `/health/ready` reports Groq chat ready. Grounded in published lessons; with 10 lessons the grounding is thin. Not verified with a live question. |
| Teacher dashboard, classes, assignments | Complete (code, tested) / Partial product | Create class, join code, heatmap, student view, assign, decisions. Never used in production (0 classrooms). No class roster management (remove student, rename, archive), no parent/guardian consent flow UI. |
| Reviewer workflow | Complete | You approved 10 lessons; published. |
| Supabase connectivity, RLS | Complete with a caveat | RLS on for all 39 `zenith` tables, 0 policies, so the browser/anon key reads nothing; only the backend (owner connection) can. Correct for this architecture. Caveat: backend authorization is the only guard, so every endpoint's role check needs the tests we have plus a review. |
| Vercel deploy | Complete | `/`, `/api/v1/health/ready` return 200, DB connected. |
| Backblaze B2 | Partial | Used for encrypted backups only. No lesson media (diagrams/images) is stored or served from B2. Weekly job not yet run in GitHub (secrets unverified). |
| Email | Missing | Resend/SMTP not set; no domain. Not needed while confirmation is off, needed for recovery. |
| Mobile and PWA | Partial / not verified live | Service worker precaches 88 files; layouts built mobile-first. Not re-tested at 360/768/1280 on the live site. |
| Monitoring | Missing | No error tracking, uptime check or log alerts. |

## 2. Content gaps (exact)

Present: CBSE; Maths Class 6 Integers (about 3 lessons), Class 7 Simple Equations, Class 8 Linear Equations. 10 lessons, 59 questions, 12 concepts.

Missing, in priority order (official NCERT book sizes, facts only, in `content/reference/ncert_books.yaml`):
- Maths: Class 6 (10 chapters, 9 missing), Class 7 (15 over two parts, 14 missing), Class 8 (14 over two parts, 13 missing), Class 9 (14, all missing), Class 10 (14, all missing).
- Science: Class 6 (12), 7 (12), 8 (13), 9 (13), 10 (13). All missing.
- Social Science, English, Hindi: not started. Out of scope until Maths and Science are solid.
- Hindi/Telugu: explanations exist only as AI-labelled translation of the tutor; lesson text is English only.
- Per lesson depth is thin: each needs explanation, 2-3 worked examples, a diagram where useful, common mistakes tied to option misconceptions, recap, 8-12 practice items across intro/core/challenge.

Rule that stays: no copying NCERT text. Lessons are original, AI-assisted drafts labelled `ai_assisted`, validated by the gates, and published only after your approval. Unfinished chapters show "Coming soon".

## 3. Remaining production work (by area)

- Auth: confirm password, show/hide, strength rules, forgot/reset password, remove the email-confirm dead branch, teacher self-signup protections (role is chosen at signup; confirm a student cannot sign up as teacher or reviewer).
- Student: first-session experience with zero data, empty states, goal/daily plan, streak and league only after consent.
- Teacher: roster management, assignment due dates and completion view, class report export, intervention follow-up.
- Adaptive accuracy: calibrate BKT parameters from real evidence once available; log selector reasons; add item-parameter updates; guard against tiny pools.
- Security: rate limits on login/signup (Vercel serverless is stateless, so use a database counter), input size limits, review all role checks, secret rotation (B2 key pasted in chat), CORS locked to the Vercel origin, security headers in `vercel.json`.
- Content pipeline: author, validate, review, publish at volume; review screen filters and batch approve of unchanged versions.
- Performance and accessibility: Lighthouse on 3G profile, keyboard and screen-reader pass, contrast, reduced motion.
- Operations: first backup run in GitHub, restore drill, uptime and error monitoring, Supabase advisor check, decision on legacy `public` tables (not touched).

## 4. Proposed design for "dynamic" quizzes

Principle from AGENTS.md: answers are never verified by an LLM and every recommendation stores its evidence. So generation is deterministic, not free-form AI.

1. Question templates (typed, versioned, reviewed like lessons): a template has parameter ranges, a stem, distractor rules tied to named misconceptions, a solver in SymPy that computes the correct answer, and a difficulty model (number size, steps, sign changes, word-problem wrapper).
2. Generation at request time: the selector picks a concept and target difficulty from the student's BKT state and Elo rating, then instantiates a template with a seed. The instance (template version, seed, parameters, answer) is stored as the attempted item, so evidence is auditable and replayable.
3. Difficulty ladder: five levels per concept. Two correct in a row at level L with no hints moves up; two wrong moves down and triggers a prerequisite probe. Challenge mode and "boss" quizzes pull from the top level.
4. AI only for drafting new templates and explanations, always labelled `ai_assisted`, validated by the same gates (the solver must agree with the declared answer on 200 random seeds), and approved by you before use.
5. Stored static items remain for conceptual and diagram questions that cannot be parameterised.

## 5. Ideas to make it a full product (pick which to include)

- Daily plan ("today": 1 revision, 1 new lesson step, 1 challenge) driven by evidence, with reasons shown.
- Mastery map per chapter with plain "why this next" explanations.
- Mistake notebook that turns wrong answers into spaced revision cards.
- Boss quiz at the end of each chapter, unlocked by mastery, with a certificate-style summary the student can show a teacher.
- Teacher "assign by weakness": pick a concept; the system builds a quiz from generated items for the class's weakest concepts.
- Parent/guardian weekly summary (needs email, hence Resend).
- Offline packs per chapter (already supported by Dexie; add explicit "download chapter").
- Peer-free challenges: classroom-scoped weekly league and quests already exist; add team goals.
- Study timer and focus mode for low-end phones; low-data mode.

## 6. Implementation phases and to-do list

Phase 0 - Baseline (small, safe)
- [ ] 0.1 Signed-in browser walkthrough of live site as student and teacher at 360/768/1280, record defects.
- [ ] 0.2 Fix auth UI: confirm password, show/hide, validation; remove confirm-email branch.
- [ ] 0.3 Forgot/reset password (needs Resend SMTP; you supply a domain and API key).
- [ ] 0.4 Security headers, CORS check, login/signup rate limit, role-escalation test.

Phase 1 - Dynamic quiz engine (core of your request)
- [ ] 1.1 Template schema + SymPy solver + distractor-from-misconception rules + validators (200-seed check).
- [ ] 1.2 `generated_items` table and migration (template, version, seed, params, answer) and evidence linkage.
- [ ] 1.3 Selector: choose concept + level from BKT/Elo, instantiate, store, serve; ladder up/down rules; repeat protection.
- [ ] 1.4 Practice, tests and teacher "assign by weakness" use generated items.
- [ ] 1.5 Tests: determinism, difficulty monotonicity, adaptation up and down, replay from stored seed.

Phase 2 - Content, Maths first
- [ ] 2.1 Lesson authoring format extended (diagram specs, common mistakes, recap) and a validator for depth minimums.
- [ ] 2.2 Maths Classes 6-8 all chapters, then 9-10 (about 70 chapters in batches of 5; you review each batch).
- [ ] 2.3 Diagrams as original SVG generated from specs; larger media to B2 with signed URLs.
- [ ] 2.4 Reference list drives "Coming soon" chapter cards.

Phase 3 - Science (same pipeline, 62 chapters in batches), then Social Science if you want.

Phase 4 - Teacher and student polish
- [ ] 4.1 Roster management, due dates, completion tracking, class report.
- [ ] 4.2 Daily plan, mistake notebook, boss quizzes, chapter offline packs.

Phase 5 - Operations
- [ ] 5.1 GitHub backup secrets and first run, restore drill.
- [ ] 5.2 Monitoring and error alerts; Lighthouse and accessibility pass.
- [ ] 5.3 Rotate the exposed B2 key. Legacy `public` tables only with your approval.

Phase 6 - End to end test of every flow as student and teacher on the live site, then fix.

## 7. Decisions needed from you
1. Approve Phase 0 and Phase 1 first (recommended): dynamic quizzes before more lessons, because more lessons on a fixed bank would still feel repetitive.
2. A domain for Resend (needed for password recovery and guardian emails), or defer recovery.
3. Which extras in section 5 to include.
4. Content volume per batch you are willing to review (I suggest 5 chapters per batch).
