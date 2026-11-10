# ZENITH Design Brief (Phase D)

Status: proposal for sign-off. Mockup: `docs/design/mockup.html`. Tokens: `docs/design/tokens.css`.

## 1. Research: what was actually seen

Evidence quality is mixed. Many sites render client-side, so the fetch tool saw only shells.

| Site | Seen | Not seen |
|---|---|---|
| Canvas Classes | Class > Subject > Chapter > numbered sections; lessons built from hook, steps, table, figure, "when it goes wrong", commit-before-reveal check, summary, 3 quick questions; flashcards, notes, reference tools (12 pages) | Crucible, planner, progress (login/JS) |
| Khan Academy (India) | Course list: Math and Science (NCERT), **Bridge** and **Revision** courses for NCERT, Karnataka, Maharashtra and Telangana boards, English grammar. Language and country switcher. Cookie wall on first load. | Lesson/exercise pages (client-rendered, spinner) |
| Brilliant | Topics grouped by subject; skill checks at end of every lesson; **unit checks that interleave prerequisite material**; personalised practice on a skill graph; review that asks the learner to explain correct answers; "kidSAFE COPPA certified" claim | Lesson anatomy, visuals |
| Seneca | Short notes + interactive courses + AI marking with instant feedback; teachers set homework; "compete with friends" claim; playful emoji-heavy tone | XP/league rules |
| Physics Wallah | Class 10 Maths topic page is the lightest layout seen: one plain link per chapter | Chapter content |
| Vedantu | Class > Subject > Chapter nav; long text articles; heavy promo cards, WhatsApp banners, video carousels, "sign-in required" PDFs | Class 6-9 pages |
| BYJU'S | Home page is a sales funnel (region notice, autoplay embed, OTP demo form) | Chapter pages |
| Duolingo | Help centre confirms leagues/streaks exist. **Not verified here.** From general knowledge (check before relying on it): weekly leagues of about 30 learners, tiers, promotion and demotion zones, ranked by XP. | Everything else |

Implication: Khan's "Bridge" courses prove the market understands prerequisite gaps. ZENITH differs by finding the gap automatically from evidence, across grades, and by showing the teacher.

## 2. Decisions: what we take, what we refuse

**Take**
- Canvas: short numbered sections, commit-before-reveal checks, trap callouts as tagged misconceptions, chapter cross-links.
- Brilliant: skill checks at lesson end, interleaved prerequisite checks, "explain why" review.
- Seneca/Khan: teacher-assigned work and class view.
- Duolingo-style small weekly leagues, rebuilt with guardrails (section 6).
- PW: text-first, one-link-per-chapter index pages.

**Refuse**
- Promo cards, banners, autoplay, OTP gates, sign-in walls in lessons, cookie walls beyond essentials, tracking query strings, mega-menus with hundreds of links.
- Global public leaderboards, paid items, streak-loss shaming, answer keys in client HTML.

## 3. Brand and feel

Concept: **the climb to the zenith**. Mastery is altitude. The logo is a peak mark. Progress uses a rising path rather than generic bars.

Feel: confident, bright, tactile. More "premium notebook" than "children's app": generous space, one strong colour per subject, crisp shadows, springy but short motion. No cartoon mascots. A small abstract companion ("the peak") may react to progress.

## 4. Design system essentials (see `tokens.css`)

- **Colour:** warm paper background, deep ink text, amber "zenith" accent for primary actions and celebration; subject colours Maths (indigo) and Science (emerald); semantic correct (green), try-again (amber-orange, never red for wrong answers), gap (coral). All text pairs meet WCAG AA; dark theme included.
- **Type:** Plus Jakarta Sans (variable, self-hosted, Latin subset, about 30 kB) for UI and headings; Noto Sans Devanagari and Noto Sans Telugu loaded only when the user picks Hindi or Telugu; KaTeX only on lessons that use maths. Body 17px, lesson text 18px, line-height 1.6.
- **Shape and depth:** 14px radius cards, 999px chips, two-layer shadows, 2px focus rings.
- **Motion:** 120/220/420 ms, spring easing for rewards; fully disabled under `prefers-reduced-motion`.
- **Touch:** 48px minimum targets, bottom navigation on phones, rail on desktop.
- **Subject theming:** each subject sets `--subject` and `--subject-soft`; components never hardcode colours.

## 5. Information architecture

Student (bottom nav): **Today** (one next step + why; assigned work; review due) | **Learn** (Class > Subject > Chapter > Lesson; chapters not yet published show "Coming soon", never padded) | **Practice** (adaptive Solve, chapter Tests) | **Climb** (concept map, league, quests, badges) | **Ask** (tutor drawer on every lesson).

Teacher: **Class** (who needs help, ranked by evidence) | **Concepts** (students x concepts heatmap with evidence counts) | **Misconceptions** | **Student** (timeline, interventions and their effect) | **Assign** | **Teach** (project a lesson, live checks) | **Review queue** (content approvals).

## 6. Competition design (competitive, safe)

- Weekly **league** of up to 20 classmates within one classroom; ranked by **Growth XP** (XP weighted by mastery gained, daily-capped so grinding cannot win).
- Tiers: Foothill, Ridge, Summit, Zenith. Top 5 promote, bottom 3 demote, weekly reset. Everyone sees their own trajectory first, then the table.
- Shown: nickname and avatar only. Teacher can switch leagues off per class. Student can hide. No real names.
- Also: daily quests, class goals ("80% of us secure on Integers by Friday"), asynchronous duels between classmates, optional speed rounds for revision, badges, chapter trophies, one free rest day per week on streaks.
- Never: public/global boards, purchases, timed competition on tests, competition XP feeding mastery or teacher evidence.
- Independent learners (no classroom): personal bests, quests, badges and challenge-by-code with a friend; no stranger leagues.

## 7. Lesson reader (the core screen)

One idea per screen on phones. Progress as a rising path. Sections: hook, explain, figure, worked example (step reveal with "why this step"), commit-then-reveal check, misconception callout, summary. Variants swap in when evidence says: simpler, visual, challenge. "Strengthen this first" banner appears only when a prerequisite is confirmed as a gap. Language toggle for explanations (AI-translated label until reviewed). Save-for-offline.

## 8. Performance budget (enforced in CI later)

Initial JS at most 170 kB gzip; route chunks lazy; fonts subset and `font-display: swap`; SVG diagrams inline or cached; images WebP with explicit sizes; LCP under 2.5 s on mid-range Android over 4G; no layout shift; service worker precaches shell and downloaded lessons only.

## 9. Component inventory

Foundations: Button, IconButton, Chip, Badge, Card, Sheet/Drawer, Tabs, Progress path, Meter, Toast, Skeleton, EmptyState. Learning: LessonSection, WorkedExample, CheckQuestion, MisconceptionCallout, FigureFrame, MathText, ConceptMap, PrereqBanner. Competition: LeagueTable, QuestCard, XPBurst, BadgeTile, StreakFlame. Teacher: ClassHeatmap, StudentRow, EvidenceChip, RecommendationCard, ReviewPanel.

## 10. Open for your sign-off

1. Direction: indigo + amber on warm paper (as in mockup) or an alternative palette?
2. League tier names and the "climb" metaphor.
3. Hindi and Telugu as UI languages from v1, or explanations only?
