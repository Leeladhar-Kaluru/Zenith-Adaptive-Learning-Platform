// API contract for the ZENITH frontend. The FastAPI backend implements exactly these shapes.
export type Role = 'student' | 'teacher' | 'admin' | 'reviewer';
export type Subject = 'maths' | 'science';
export type Band = 'unassessed' | 'learning' | 'secure' | 'gap_suspected' | 'gap_confirmed';

export interface Profile {
  id: string;
  displayName: string;
  nickname: string;
  avatar: string;
  role: Role;
  grade: number | null;
  boardId: string | null;
  language: 'en' | 'hi' | 'te';
  onboardingCompleted: boolean;
  consentStatus: 'not_required' | 'pending' | 'granted';
  classroomIds: string[];
}

export interface Chapter {
  id: string;
  slug: string;
  grade: number;
  subject: Subject;
  number: number;
  title: string;
  status: 'published' | 'coming_soon';
  lessonCount: number;
  conceptCount: number;
  progress: { done: number; total: number } | null;
}

export interface LessonStub {
  id: string;
  title: string;
  order: number;
  minutes: number;
  state: 'done' | 'current' | 'todo';
}

export interface PrereqGap {
  conceptId: string;
  title: string;
  grade: number;
  lessonId: string | null;
  band: Band;
}

export interface ChapterDetail {
  chapter: Chapter;
  summary: string;
  lessons: LessonStub[];
  prerequisites: PrereqGap[];
}

export type Block =
  | { id: string; kind: 'text'; heading?: string; html: string }
  | { id: string; kind: 'figure'; svg: string; alt: string; caption?: string }
  | { id: string; kind: 'widget'; widget: 'numberline' | 'balance' | 'fraction'; config: Record<string, number | string> }
  | { id: string; kind: 'example'; heading: string; prompt: string; steps: string[] }
  | { id: string; kind: 'callout'; tone: 'watch' | 'remember' | 'real'; html: string }
  | { id: string; kind: 'check'; item: PublicItem }
  | { id: string; kind: 'summary'; points: string[] };

export interface Lesson {
  id: string;
  chapterSlug: string;
  chapterTitle: string;
  subject: Subject;
  title: string;
  order: number;
  total: number;
  minutes: number;
  prevId: string | null;
  nextId: string | null;
  prereqGap: PrereqGap | null;
  blocks: Block[];
  siblings: LessonStub[];
}

export interface PublicItem {
  id: string;
  stem: string;
  options: Array<{ key: string; text: string }>;
  hintCount: number;
  difficulty: 'intro' | 'standard' | 'challenge';
}

export interface EvidenceRequest {
  itemId: string;
  choice: string;
  hintsUsed: number;
  ms: number;
  context: 'learn_check' | 'solve' | 'test' | 'probe';
  clientEventId: string;
}
export interface EvidenceResult {
  correct: boolean;
  correctKey: string;
  feedback: string;
  misconception: string | null;
  xp: number;
  concept: { id: string; title: string; band: Band };
  next: NextStep | null;
}

export interface NextStep {
  kind: 'lesson' | 'practice' | 'prereq' | 'challenge' | 'review' | 'probe' | 'assigned';
  title: string;
  reason: string;
  minutes: number;
  href: string;
  evidenceCount: number;
}

export interface Today {
  nextStep: NextStep | null;
  streak: number;
  xp: number;
  level: number;
  levelProgress: number;
  assigned: Array<{ id: string; title: string; due: string; done: number; total: number; href: string }>;
  recent: Array<{ chapter: string; lesson: string; href: string; progress: number }>;
}

export interface League {
  tier: 'foothill' | 'ridge' | 'summit' | 'zenith';
  endsAt: string;
  rows: Array<{ rank: number; nickname: string; avatar: string; xp: number; me: boolean; zone: 'up' | 'stay' | 'down' }>;
}
export interface Climb {
  league: League | null;
  leagueDisabledReason: 'no_classroom' | 'teacher_off' | 'opted_out' | null;
  quests: Array<{ id: string; title: string; icon: string; done: number; total: number }>;
  goal: { title: string; percent: number } | null;
  badges: Array<{ id: string; title: string; hint: string; icon: string; earned: boolean }>;
  streak: { days: number; restDayAvailable: boolean };
}

export interface MapNode { id: string; title: string; grade: number; band: Band; x: number; y: number }
export interface MapGraph { chapterSlug: string; nodes: MapNode[]; edges: Array<[string, string]> }

export interface TutorReply { reply: string; citations: Array<{ title: string; heading: string }>; language: string; aiTranslated: boolean; degraded: boolean }

export interface ClassSummary { id: string; name: string; grade: number; subject: Subject; students: number; joinCode: string }
export interface Heatmap { concepts: Array<{ id: string; title: string }>; students: Array<{ id: string; nickname: string; avatar: string; cells: Band[] }> }
export interface Recommendation { id: string; text: string; evidence: string; students: number; lessonId: string | null; lessonTitle: string | null }
export interface ClassOverview { cls: ClassSummary; heatmap: Heatmap; recommendations: Recommendation[]; needsHelp: Array<{ id: string; nickname: string; avatar: string; reason: string }> }
export interface StudentDetail {
  id: string; nickname: string; avatar: string; grade: number;
  concepts: Array<{ id: string; title: string; band: Band; evidenceCount: number }>;
  timeline: Array<{ at: string; text: string }>;
  interventions: Array<{ concept: string; before: Band; after: Band | null; status: 'open' | 'closed' }>;
}

export interface ReviewQueueItem { id: string; title: string; chapter: string; grade: number; subject: Subject; status: 'in_review' | 'changes_requested' | 'approved' | 'published'; gates: { passed: number; total: number }; origin: 'human' | 'ai_assisted' }
export interface ReviewDetail {
  id: string; title: string; chapter: string; origin: 'human' | 'ai_assisted';
  gates: Array<{ name: string; passed: boolean; detail: string; manual?: boolean }>;
  flags: Array<{ id: string; severity: 'info' | 'warn'; text: string }>;
  lesson: Lesson;
}
export interface OfflinePack { chapterSlug: string; title: string; bytes: number; lessons: number; savedAt: string }
