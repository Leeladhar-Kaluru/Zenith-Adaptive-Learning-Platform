# Progress — teamwork_reviewer_m4_2

Last visited: 2026-11-08T03:13:00Z
Status: In Progress - Reviewing Frontend Integration & API contracts. Build task running.

## Findings Discovered:
1. Critical Integrity / Type Mismatch: `submitPracticeAttempt` in `api.ts` and `syncManager.ts` sends `hints_used` as an integer (`hintsUsed ?? 0` and `hintsUsed.length`). Backend `PracticeSubmitRequest` strictly requires `Optional[List[str]]`. Live and sync calls fail with HTTP 422 Unprocessable Entity.
2. Integrity Violation / Fabricated Offline Results: In `PracticePage.tsx`, fallback submission sets hardcoded `isCorrect: true`, `pKnow: 0.75`, `masteryBand: 'approaching'`.
3. Offline Caching Failure in `LessonReaderPage.tsx`: `saveLessonOffline` persists `{ content: resource }` into `packageData`, but `getOfflineLesson` retrieval checks `cached.packageData?.package`, which is undefined. Saved offline lessons can never be restored; it always falls back to synthesized dummy data.
4. Hardcoded Rule 2 Violations across Views: `HomePage.tsx`, `ChapterPage.tsx`, `ExplorePage.tsx`, `LearningMapPage.tsx`, `AchievementsPage.tsx` contain hardcoded fallbacks with fabricated user progress, completed resources (e.g. `completionPct: 20`, `isCompleted: true`), fake mastery scores, and fake unlocked badges.
5. Missing Caching Configuration in `vercel.json`: No immutable cache headers for hashed assets and no revalidation rules for `index.html`.
6. Visible Product Name Violation: `ErrorBoundary.tsx` displays "SETU encountered a display issue loading this section."
