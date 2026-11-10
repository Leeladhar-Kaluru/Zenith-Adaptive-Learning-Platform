// Shapes returned by the ZENITH API (backend/app/api/v1). Kept in sync by hand and by the backend tests.
export type Role = 'student' | 'teacher' | 'admin' | 'reviewer';
export type Subject = string;
export type Band = 'unassessed' | 'learning' | 'secure' | 'gap_suspected' | 'gap_confirmed';
export type Lang = 'en' | 'hi' | 'te';

export interface Profile {
  id: string; displayName: string; nickname: string; avatar: string; role: Role; grade: number | null; boardId: string | null;
  language: Lang; goals: string[]; subjects: string[]; onboardingCompleted: boolean; consentStatus: string; classroomIds: string[]; leagueOptOut: boolean;
}
export interface Boards { boards: Array<{ id: string; name: string }>; subjects: Array<{ id: string; name: string }>; grades: number[] }

export interface Chapter {
  id: string; slug: string; grade: number; subject: Subject; number: number | null; title: string; status: 'published' | 'coming_soon';
  lessonCount: number; conceptCount: number; progress: { done: number; total: number } | null;
}
export interface LessonStub { id: string; title: string; order: number; minutes: number; state: 'done' | 'current' | 'todo' }
export interface PrereqGap { conceptId: string; title: string; grade: number; band: Band; lessonId: string | null; distance?: number }
export interface ChapterDetail {
  chapter: Chapter; summary: string; objectives: string[]; lessons: LessonStub[];
  concepts: Array<{ id: string; title: string; band: Band; evidence: number }>; prerequisites: PrereqGap[];
}

export interface PublicItem {
  id: string; kind: 'mcq' | 'multi' | 'truefalse' | 'numeric' | 'fill' | 'match' | 'find_error' | 'label_diagram'; stem: string; difficulty: 'intro' | 'standard' | 'challenge'; hintCount: number;
  options?: Array<{ key: string; text: string }>; steps?: string[]; svg?: string; regions?: string[]; labels?: string[]; unit?: string; left?: string[]; right?: string[];
}
export type Block =
  | { id: string; kind: 'text'; heading?: string; html: string }
  | { id: string; kind: 'figure'; svg: string; asset?: string; imageUrl?: string | null; alt: string; caption?: string }
  | { id: string; kind: 'widget'; widget: 'numberline' | 'balance' | 'fraction' | 'sim_linegraph' | 'sim_equation' | 'sim_spinner' | 'sim_density' | 'data_chart' | 'atlas'; config: Record<string, number | string>; task?: string }
  | { id: string; kind: 'example'; heading: string; prompt: string; steps: string[] }
  | { id: string; kind: 'callout'; tone: 'watch' | 'remember' | 'real'; html: string }
  | { id: string; kind: 'check'; item: PublicItem }
  | { id: string; kind: 'summary'; points: string[] };
export interface Lesson {
  id: string; versionId: string; chapterSlug: string; chapterTitle: string; subject: Subject; title: string; order: number; total: number; minutes: number;
  objectives: string[]; prevId: string | null; nextId: string | null; prereqGap: PrereqGap | null; blocks: Block[]; siblings: LessonStub[];
  related: Array<{ lessonId: string; title: string; chapterSlug: string; why: string }>; completed: boolean;
  credits: Array<{ text: string; url: string; licence: string }>;
}

export type Response = Record<string, unknown>;
export interface EvidenceRequest { itemId: string; response: Response; hintsUsed: number; ms: number; context: 'learn_check' | 'solve' | 'test' | 'probe'; clientEventId: string; sessionId?: string; occurredAt?: string }
export interface EvidenceResult {
  correct: boolean; score: number; reveal: unknown; feedback: string; misconception: string | null; xp: number; alreadyRecorded: boolean; newBadges: string[];
  concepts: Array<{ id: string; title: string; band: Band; pKnown: number; evidence: number; confidence: 'low' | 'medium' | 'high' }>;
  changes: Array<{ concept: string; title: string; from: Band; to: Band; level: number }>;
  levelChange?: { concept: string; from: number; to: number; reason: string; signal: string } | null;
}
export interface NextPractice { item: PublicItem; scope: string; generated?: boolean; ladderLevel?: number; concept: { id: string; title: string; level: number; band: Band }; why: string }

export interface NextStep { kind: string; title: string; reason: string; href: string; minutes: number; evidenceCount: number; conceptId?: string; assignment?: string }
export interface Assigned { id: string; kind: string; title: string; note: string | null; due: string | null; done: number; total: number; href: string; complete: boolean }
export interface LevelInfo { level: number; xp: number; intoLevel: number; forNext: number; progress: number }
export interface StreakInfo { days: number; restDayAvailable: boolean; activeToday: boolean }
export interface Quest { id: string; title: string; icon: string; done: number; total: number }
export interface Badge { id: string; title: string; hint: string; icon: string; earned: boolean; earnedAt: string | null }
export interface Milestone { label: string; value: number; next: number | null }
export interface Today {
  nextStep: NextStep | null; alternatives: NextStep[]; streak: StreakInfo; xp: LevelInfo; todayXp: number; goals: Quest[]; assigned: Assigned[];
  revision: Array<{ conceptId: string; title: string; dueAt: string }>; recent: Array<{ lessonId: string; title: string; chapter: string; status: string }>;
  badges: Badge[]; milestones: Milestone[];
  mission?: Mission;
}
export interface Mission { items: Array<{ slot: 'revision' | 'new' | 'challenge'; title: string; reason: string; minutes: number; evidenceCount: number; href: string; kind: string }>; totalMinutes: number; reason: string; href: string }

export interface Overview {
  concepts: Array<{ id: string; title: string; grade: number; subject: string; band: Band; pKnown: number; evidence: number; correct: number; confidence: 'low' | 'medium' | 'high'; level: number; lastAt: string | null }>;
  chapters: Array<{ slug: string; title: string; subject: string; lessonsDone: number; lessons: number; concepts: Partial<Record<Band, number>>; conceptTotal: number }>;
  activity: Array<{ day: string; answers: number; correct: number; xp: number }>; streak: StreakInfo; xp: LevelInfo; badges: Badge[]; mistakes: number; revisionDue: number; milestones: Milestone[];
}
export interface Mistake { itemId: string; stem: string; explanation: string; missedTimes: number; resolved: boolean; lastMissedAt: string; misconception: string | null; kind: string; concepts: string[] }

export interface NotebookGroup { misconception: string; code: string; concept: { id: string; title: string }; times: number; lastAt: string; resolved: boolean; examples: Array<{ stem: string; explanation: string }>; practice: string }
export interface Notebook { groups: NotebookGroup[]; openCount: number; resolvedCount: number; note: string }
export interface BossStatus { chapter: string; unlocked: boolean; meanMastery: number; needed: number; passMark: number; reason: string; concepts: Array<{ id: string; title: string; p: number; n: number }> }

export interface Gamification {
  league: { tier: 'foothill' | 'ridge' | 'summit' | 'zenith'; endsAt: string; classroom: string; rows: Array<{ rank: number; nickname: string; avatar: string; xp: number; me: boolean; zone: 'up' | 'stay' | 'down' }> } | null;
  reason: 'no_classroom' | 'teacher_off' | 'opted_out' | 'too_few' | null; quests: Quest[]; badges: Badge[]; streak: StreakInfo; xp: LevelInfo;
}

export interface TestSession { id: string; kind: string; chapter: string | null; conceptId: string | null; status: 'active' | 'submitted' | 'expired'; timeLimitS: number | null; remainingS?: number | null; total: number; items?: PublicItem[]; answered?: string[]; summary?: TestSummary }
export interface TestSummary {
  right: number; total: number; answered: number; accuracy: number; note: string;
  byConcept: Array<{ conceptId: string; title: string; right: number; total: number; band: Band; evidence: number; confidence: string }>;
  mistakes: Array<{ itemId: string; stem: string; answered: boolean; explanation: string; misconception: string | null }>;
  suggestions: Array<{ conceptId: string; title: string; action: string; why: string; href: string }>;
  boss?: boolean; passed?: boolean; passMark?: number;
}
export interface Revision { due: Array<{ conceptId: string; title: string; dueAt: string }>; cards: Array<{ id: string; conceptId: string; front: string; back: string }> }
export interface Explore { available: Array<{ key: string; title: string; text: string; href: string; count: number }>; planned: Array<{ key: string; title: string; text: string }> }
export interface SearchResults {
  chapters: Chapter[]; lessons: Array<{ id: string; title: string; chapter: string; grade: number }>; concepts: Array<{ id: string; title: string; grade: number; lessonId: string | null }>;
}
export interface MapGraph { chapterSlug: string; nodes: Array<{ id: string; title: string; grade: number; band: Band; inChapter: boolean; x: number; y: number; lessonId: string | null; mastery: number; nextUnlock: boolean }>; edges: Array<[string, string]> }
export interface TutorReply { reply: string; citations: Array<{ title: string; heading: string }>; language: string; aiTranslated: boolean; degraded: boolean }

export interface ClassSummary { id: string; name: string; grade: number; subject: string; students: number; joinCode: string; leaguesEnabled: boolean }
export interface Suggestion { key: string; text: string; evidence: string; students: number; studentIds: string[]; conceptId: string; lessonId: string | null; lessonTitle: string | null }
export interface ClassOverview {
  cls: ClassSummary; concepts: Array<{ id: string; title: string }>;
  heatmap: Array<{ id: string; nickname: string; avatar: string; cells: Array<{ band: Band; evidence: number }> }>;
  needsHelp: Array<{ id: string; nickname: string; avatar: string; reason: string }>; suggestions: Suggestion[];
  trend: Array<{ day: string; answers: number; accuracy: number }>; assignments: Array<{ id: string; title: string; kind: string; due: string | null; done: number; students: number }>;
}
export interface StudentDetail {
  id: string; nickname: string; name: string; avatar: string; grade: number;
  concepts: Array<{ id: string; title: string; band: Band; evidence: number; correct: number; confidence: string }>;
  timeline: Array<{ at: string; text: string; context: string }>; interventions: Array<{ concept: string; before: number; after: number | null; status: 'open' | 'closed'; startedAt: string }>;
  mistakes: Mistake[]; assignments: Assigned[];
  levels: Array<{ concept: string; title: string; level: number; reason: string; updatedAt: string }>;
  activity: { days: number; readingMinutes: number; lessonsOpened: number; hintsOpened: number; answerChanges: number; simulationMoves: number };
}
export interface CatalogChapter { slug: string; title: string; lessons: Array<{ id: string; title: string }> }

export interface ReviewQueueItem { id: string; title: string; chapter: string; grade: number; subject: string; status: string; version: number; origin: 'human' | 'ai_assisted'; gates: { passed: number; total: number } }
export interface ReviewDetail {
  id: string; title: string; chapter: string; status: string; version: number; origin: 'human' | 'ai_assisted'; reviewNote: string | null;
  gates: Array<{ name: string; passed: boolean; detail: string; manual: boolean }>; flags: Array<{ id: string; severity: 'info' | 'warn'; text: string }>;
  lesson: Lesson; answers: Array<{ key: string; kind: string; stem: string; difficulty: string; purpose: string; answer: Record<string, unknown>; explanation: string }>;
}
export interface Coverage { slug: string; title: string; grade: number; subject: string; status: string; lessons: number; published: number }
