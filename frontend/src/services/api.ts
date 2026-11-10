// ZENITH API Service Client - Typed contracts connecting frontend to backend

const rawBase = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
export const API_BASE = rawBase
  ? rawBase.endsWith('/api/v1')
    ? rawBase
    : `${rawBase}/api/v1`
  : '/api/v1';

export interface UserProfileData {
  id: string;
  email: string | null;
  role: 'student' | 'teacher';
  displayName: string;
  grade?: number | null;
  boardId?: string | null;
  preferredLanguage?: string | null;
  subjectsInterested?: string[];
  learningGoals?: string[];
  dailyGoalMinutes?: number | null;
  canTeach?: boolean;
  academicContextComplete?: boolean;
  accessibilityPreferences?: {
    font_size?: string;
    reduced_motion?: boolean;
    high_contrast?: boolean;
    pace?: 'short' | 'steady' | 'long';
  };
  onboardingCompleted?: boolean;
  tourCompleted?: boolean;
}

export interface CatalogueBoard {
  id: string;
  code: string;
  name: string;
  region?: string | null;
  officialUrl?: string | null;
}

export interface CatalogueSubject {
  id: string;
  code: string;
  canonicalName: string;
  name: string;
}

export interface CatalogueLanguage {
  id: string;
  bcp47Tag: string;
  nativeName: string;
  script: string;
}

export interface AuthResponse {
  accessToken: string;
  user: UserProfileData;
}

export interface CatalogueResource {
  id: string;
  title: string;
  description?: string;
  boardId: string;
  board: string;
  grade: number;
  subjectId: string;
  subject: string;
  medium?: string;
  edition?: string;
  externalUrl?: string;
  totalPages?: number;
  rights?: {
    licenseName: string;
    canLink: boolean;
    canDownload: boolean;
    canStore: boolean;
    canProcess: boolean;
    canOfflineCache: boolean;
  };
}

export interface IngestionStatus {
  documentId: string;
  status: 'selected' | 'uploading' | 'stored' | 'extracting' | 'extracted' | 'indexing' | 'indexed' | 'analysing' | 'awaiting_review' | 'generating' | 'ready' | 'failed' | 'needs_ocr';
  filename: string;
  pageCount?: number;
  chunkCount?: number;
  pagesRead?: number;
  pagesNeedingOcr?: number;
  errorMessage?: string;
  progressMessage?: string;
  deduplicated?: boolean;
  canBuildPath?: boolean;
  outlineMessage?: string;
  chapters?: Array<{ title: string; pageStart: number; pageEnd: number }>;
}

export interface UserDocument {
  id: string;
  documentId: string;
  filename: string;
  status: string;
  pageCount?: number;
  chunkCount?: number;
  pagesRead?: number;
  pagesNeedingOcr?: number;
  sizeBytes?: number;
  errorMessage?: string;
  progressMessage?: string;
  deduplicated?: boolean;
  createdAt?: string;
  chapters?: Array<{ title: string; pageStart: number; pageEnd: number }>;
}

export interface LearningPathItem {
  id: string;
  documentId?: string | null;
  title: string;
  grade: number;
  subjectId: string;
  status: string;
  progressPercent: number;
  totalLessons: number;
  readyLessons: number;
  sourceTitle?: string;
  firstLessonId?: string;
  lessons?: Array<{ id: string; title: string; status: string; sequence: number }>;
}

export interface ClassroomData {
  id: string;
  name: string;
  grade: number;
  boardId: string;
  subjectScope: string;
  joinCode: string | null;
  memberCount: number;
  createdAt: string;
}

export type EvidenceBand =
  | 'not_enough_evidence'
  | 'developing'
  | 'approaching'
  | 'demonstrated';

export interface EvidenceConceptRow {
  conceptId: string;
  band: EvidenceBand;
  score: number;
  evidenceCount: number;
  calculatedAt: string | null;
}

export interface EvidenceMatrixRow {
  studentId: string;
  studentName: string;
  profileMissing?: boolean;
  concepts: EvidenceConceptRow[];
  conceptsDemonstrated: number;
  totalConcepts: number;
  accuracyRate: number;
  accuracyKnown?: boolean;
  recentAttemptsCount: number;
  evidenceBand: EvidenceBand;
  lastActive: string;
  minutesStudied?: number;
  readingTitle?: string | null;
  improvement?: string;
  heatmap?: Array<{ date: string; seconds: number }>;
  focus?: string;
}

export interface TeacherActionRow {
  id: string;
  studentId: string;
  conceptId: string;
  actionType: string;
  notes: string;
  status: 'proposed' | 'accepted' | 'dismissed' | 'edited' | 'superseded';
  studentResponse?: { decision: string; note?: string; respondedAt?: string } | null;
  createdAt: string;
}

export interface RosterMember {
  studentId: string;
  studentName: string;
  profileMissing: boolean;
  status: 'active' | 'removed';
  joinedAt: string | null;
}

export interface EvidenceMatrixResponse {
  classroomId: string;
  name?: string;
  grade?: number;
  subjectScope?: string;
  joinCode?: string | null;
  totalStudents: number;
  matrix: EvidenceMatrixRow[];
  actions: TeacherActionRow[];
  classGaps?: ClassGapRow[];
}

export interface ClassGapRow {
  conceptId: string;
  studentsWithEvidence: number;
  averageScore: number | null;
  bands: Record<EvidenceBand, number>;
  studentsNeedingSupport: number;
  supportNames: string[];
  priority: number;
}

export interface DashboardStats {
  currentStreak: number;
  longestStreak: number;
  totalMinutesStudied: number;
  totalSessions: number;
  averageAccuracy: number;
  totalQuestionsAttempted: number;
}

export interface ActivityHeatmapDay {
  date: string;
  seconds: number;
  minutes: number;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}

export interface ConceptMasteryItem {
  conceptId: string;
  band: 'demonstrated' | 'approaching' | 'developing' | 'not_enough_evidence';
  score: number;
  evidenceCount: number;
  calculatedAt: string | null;
  needsRemediation: boolean;
}

export interface RecentAttemptItem {
  id: string;
  lessonTitle: string;
  score: number;
  isCorrect: boolean;
  hintsUsed: number;
  elapsedSeconds: number;
  occurredAt: string | null;
}

export interface LearnerEvidenceItem {
  conceptId: string;
  label: string;
  band: EvidenceBand;
  score: number | null;
  evidenceCount: number;
  calculatedAt?: string | null;
}

export interface LearnerInsightBlock {
  state: 'measured' | 'no_evidence';
  detail: string;
}

export interface LearnerAccuracy extends LearnerInsightBlock {
  overall: number | null;
  lastSevenDays: number | null;
  previousSevenDays: number | null;
  trend: 'improving' | 'needs_support' | 'steady' | 'starting' | 'no_evidence';
  practiceAccuracy?: number | null;
  checkpointAccuracy?: number | null;
}

export interface LearnerPace extends LearnerInsightBlock {
  medianAnswerSeconds: number | null;
  medianSessionMinutes: number | null;
  dailyGoalMinutes: number | null;
  goalProgress: number | null;
  label: string;
}

export interface LearnerHints extends LearnerInsightBlock {
  hintedAttempts: number;
  totalAttempts: number;
  hintRate: number | null;
  averageHints: number | null;
  accuracyWithHints: number | null;
  accuracyWithoutHints: number | null;
  label: string;
}

export interface LearnerRoutineWindow {
  id: string;
  label: string;
  minutes: number;
  sessions: number;
  attempts: number;
  correct: number;
  accuracy: number | null;
}

export interface LearnerRoutine extends LearnerInsightBlock {
  windows: LearnerRoutineWindow[];
  bestWindow: LearnerRoutineWindow | null;
  currentStreak: number;
  longestStreak: number;
  activeDays: number;
  consistencyScore: number;
  consistencyLabel: string;
  weekdayMinutes: number;
  weekendMinutes: number;
  timezoneNote?: string;
}

export interface LearnerMastery extends LearnerInsightBlock {
  concepts: LearnerEvidenceItem[];
  strengths: LearnerEvidenceItem[];
  focusAreas: LearnerEvidenceItem[];
  bands: {
    demonstrated: number;
    approaching: number;
    developing: number;
    notEnoughEvidence: number;
  };
}

export interface LearnerHabit {
  id: string;
  tone: 'positive' | 'neutral' | 'watch';
  title: string;
  detail: string;
}

export interface LearnerInsights {
  generatedAt: string;
  state: 'measured' | 'no_evidence';
  confidence: 'none' | 'low' | 'medium' | 'high';
  confidenceDetail: string;
  summary: string;
  library: { activePaths: number; readyLessons: number };
  evidence: {
    studyEvents: number;
    gradedAttempts: number;
    practiceAttempts: number;
    checkpointAttempts: number;
    conceptEvidence: number;
    activeDays: number;
    totalMinutes: number;
  };
  accuracy: LearnerAccuracy;
  pace: LearnerPace;
  hintReliance: LearnerHints;
  routine: LearnerRoutine;
  mastery: LearnerMastery;
  habits: LearnerHabit[];
}

export interface StudyPlanTask {
  id: string;
  kind: 'remediate' | 'review' | 'continue' | 'next_lesson' | 'practice' | 'stretch';
  priority: number;
  slot: string;
  title: string;
  reason: string;
  actionLabel: string;
  pathId: string;
  pathTitle: string;
  subjectId: string;
  subjectLabel: string;
  lessonId: string | null;
  lessonTitle: string | null;
  conceptId: string | null;
  conceptLabel: string | null;
  evidence: Record<string, unknown>;
}

export interface StudyPlanBook {
  pathId: string;
  title: string;
  documentTitle: string | null;
  grade: number;
  subjectId: string;
  subjectLabel: string;
  status: string;
  totalLessons: number;
  readyLessons: number;
  completedLessons: number;
  mastery: {
    demonstrated: number;
    approaching: number;
    developing: number;
    notEnoughEvidence: number;
  };
  strongestConcept: LearnerEvidenceItem | null;
  focusConcept: LearnerEvidenceItem | null;
  inProgressLesson: { lessonId: string; title: string } | null;
  nextLesson: { lessonId: string; title: string } | null;
}

export interface StudyPlan {
  generatedAt: string;
  state: 'active' | 'preparing' | 'empty';
  summary: string;
  subjectMix: string[];
  bookCount: number;
  taskCount: number;
  tasks: StudyPlanTask[];
  books: StudyPlanBook[];
  roadmap: Array<{
    pathId: string;
    title: string;
    subjectLabel: string;
    lessons: Array<{
      lessonId: string;
      title: string;
      sequence: number;
      status: string;
      attempts: number;
      readingMinutes: number;
    }>;
  }>;
  counts: {
    completedLessons: number;
    readyLessons: number;
    totalLessons: number;
    waitingBooks: number;
  };
}

export interface CoachRootGap {
  conceptId: string;
  label: string;
  band: EvidenceBand;
  score: number | null;
  evidenceCount: number;
  lessonTitle: string;
  sequence: number;
  distance: number;
  reason: string;
}

export interface CoachCard {
  id: string;
  scope: 'attempt' | 'lesson';
  tone?: 'celebrate' | 'retry';
  headline?: string;
  body: string;
  conceptId?: string | null;
  conceptLabel?: string | null;
  rootGap?: CoachRootGap | null;
  mastery?: { band?: string; score?: number; evidenceCount?: number };
  nextStep?: { title?: string; reason?: string; action?: string };
  keyPoint?: { title: string; body: string } | null;
  source?: { page: number; title: string; excerpt: string } | null;
  studyTip?: { title: string; body: string } | null;
  evidence?: Record<string, unknown>;
}

export interface LessonCoachMoment {
  id: string;
  kind: 'key_point' | 'source_spotlight' | 'fun_fact' | 'study_tip' | 'challenge';
  title: string;
  body: string;
  evidence?: string;
  source?: { page: number; title: string };
}

export interface LessonCoaching {
  lessonId: string;
  lessonTitle: string;
  state: 'ready' | 'no_source_material';
  intro: string;
  difficulty: 'standard' | 'challenge';
  challengeCount: number;
  concepts: string[];
  developingConcepts: string[];
  moments: LessonCoachMoment[];
  autoShowId: string | null;
  generatedAt: string;
}

export interface SmartCheckQuestion {
  questionKey: string;
  lessonVersionId: string;
  lessonId: string;
  pathId: string;
  lessonTitle: string;
  pathTitle: string;
  subjectId: string;
  subjectLabel: string;
  conceptId: string;
  conceptLabel: string;
  prompt: string;
  type: string;
  options: string[];
  difficulty: string;
  why: string;
  mastery: { band: EvidenceBand; score: number | null; evidenceCount: number };
}

export interface SmartCheckResponse {
  state: 'ready' | 'no_questions';
  message: string;
  questions: SmartCheckQuestion[];
  maxQuestions: number;
  coverage?: {
    availableConcepts: number;
    measuredConcepts: number;
    unknownConcepts: number;
  };
}

export interface SmartCheckNextResponse {
  state: 'question' | 'complete';
  stopReason: 'max_questions' | 'enough_evidence' | 'no_more_questions' | null;
  message: string;
  question: SmartCheckQuestion | null;
  answeredCount: number;
  remaining?: number;
}

export interface StudentDashboardResponse {
  profile: UserProfileData;
  stats: DashboardStats;
  activityHeatmap: ActivityHeatmapDay[];
  conceptMastery: ConceptMasteryItem[];
  recentAttempts: RecentAttemptItem[];
  classrooms: Array<{
    id: string;
    name: string;
    grade: number;
    subjectScope: string;
    joinCode: string;
    joinedAt: string;
  }>;
  understanding?: LearnerInsights;
  teaching?: { canTeach: boolean; ownedClassrooms: number };
}

export interface AttemptSubmission {
  lessonVersionId: string;
  questionKey: string;
  response: unknown;
  hintLevel?: number;
  hintsUsed?: string[];
  elapsedSeconds?: number;
  attemptKind?: 'practice' | 'checkpoint';
  syncIdempotencyKey?: string;
}

export interface AttemptResult {
  attemptId: string;
  isCorrect: boolean;
  score: number;
  correctAnswer?: unknown;
  feedback: string;
  mastery: { band: string; score: number; evidenceCount: number; explanation: string };
  nextAction: {
    action: string;
    title: string;
    reason: string;
    canAdvance: boolean;
    remediationInjected?: boolean;
    remediationLessonId?: string;
  };
  coaching?: CoachCard | null;
  alreadyRecorded: boolean;
  personalCoach?: 'queued' | null;
  conceptId?: string | null;
}

export interface PersonalCoachNote {
  headline: string;
  body: string;
  studyTipTitle: string;
  studyTipBody: string;
  analyzedAttempts: number;
}

export interface CoachNoteResponse {
  status: 'ready' | 'pending' | 'none';
  note?: { id: string; conceptId: string; content: PersonalCoachNote; completedAt: string } | null;
}

export interface MyClassroomEntry {
  id: string;
  name: string;
  grade: number;
  subjectScope: string;
  boardId: string | null;
  role: 'teacher' | 'student' | 'co_teacher';
  joinCode: string | null;
  teacherId: string;
  teacherName: string;
}

export interface ClassroomChatMessage {
  id: string;
  classroomId: string;
  senderId: string;
  senderName: string;
  kind: 'group' | 'direct';
  recipientId: string | null;
  body: string;
  createdAt: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('setu_auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const REQUEST_TIMEOUT_MS = 120000;
const RETRYABLE_STATUSES = new Set([502, 503, 504]);

async function fetchOnce(endpoint: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      signal: controller.signal
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...(options.headers || {})
  };

  let response: Response;
  try {
    response = await fetchOnce(endpoint, { ...options, headers });
  } catch (firstError) {
    try {
      response = await fetchOnce(endpoint, { ...options, headers });
    } catch {
      throw firstError;
    }
  }

  if (!response.ok && RETRYABLE_STATUSES.has(response.status)) {
    const retried = await fetchOnce(endpoint, { ...options, headers });
    if (retried.ok) return retried.json();
    response = retried;
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    throw new ApiError(errorDetail || `Request failed with status ${response.status}`, response.status);
  }

  return response.json();
}

// -------------------------------------------------------------
// ZENITH Curriculum, Rewards, Practice & Tutor Types
// -------------------------------------------------------------

export interface LibraryChapterItem {
  id: string;
  slug: string;
  chapterNumber: number;
  title: string;
  description: string;
  conceptCount: number;
  resourceCount: number;
  estimatedMinutes: number;
  isEnrolled: boolean;
  completionPct: number;
}

export interface LibraryCatalogueResponse {
  curriculumId?: string;
  board?: { id: string; code: string; name: string };
  boards?: string[];
  grade: number;
  subject?: { id: string; code: string; name: string };
  subjects?: Array<{ id: string; name: string; code: string }> | string[];
  totalChapters?: number;
  totalConcepts?: number;
  totalLessons?: number;
  chapters: LibraryChapterItem[];
}

export interface ChapterConcept {
  id: string;
  slug: string;
  title: string;
  description: string;
  grade: number;
  order: number;
  pL0?: number;
  pT?: number;
  pG?: number;
  pS?: number;
}

export interface ChapterResource {
  id: string;
  resourceId?: string;
  lessonKey: string;
  resourceKind?: 'lesson' | 'worked_examples' | 'quick_revision' | 'formula_sheet' | 'practice_set';
  title: string;
  sequence: number;
  estimatedMinutes: number;
  status?: string;
  file?: string;
  isCompleted?: boolean;
}

export interface ChapterDetailResponse {
  id: string;
  slug: string;
  chapterNumber: number;
  title: string;
  description: string;
  grade: number;
  subjectId: string;
  boardId: string;
  estimatedMinutes: number;
  concepts: ChapterConcept[];
  resources: ChapterResource[];
  isEnrolled: boolean;
  completionPct: number;
  prerequisites?: Array<{ id: string; title: string }>;
}

export interface ResourcePackageResponse {
  id: string;
  resourceId: string;
  lessonKey: string;
  title: string;
  sequence: number;
  package: {
    schemaVersion?: string;
    lessonId?: string;
    title: string;
    grade?: number;
    subjectId?: string;
    estimatedMinutes?: number;
    objectives?: string[];
    blocks?: Array<{
      blockId?: string;
      kind: 'explanation' | 'definition' | 'summary' | 'callout';
      heading?: string;
      content: string;
    }>;
    workedExamples?: Array<{
      prompt: string;
      steps: string[];
      answer: string;
    }>;
    practice?: Array<{
      questionId: string;
      type?: 'multiple_choice';
      prompt: string;
      options: string[];
      conceptIds?: string[];
      difficulty?: string;
      hints?: string[];
      feedback?: string;
    }>;
  };
}

export interface ConceptDagNode {
  id: string;
  title?: string;
  name?: string;
  description?: string;
  grade?: number;
  order?: number;
  pKnow?: number;
  masteryScore?: number;
  masteryBand?: 'mastered' | 'approaching' | 'developing' | 'not_started' | 'demonstrated' | 'not_enough_evidence';
  isGap?: boolean;
  x?: number;
  y?: number;
}

export interface ConceptDagEdge {
  from: string;
  to: string;
  relationship?: 'prerequisite' | 'corequisite';
  weight?: number;
  prerequisiteId?: string;
  dependentId?: string;
}

export interface ConceptDagMapResponse {
  chapterSlug: string;
  chapterTitle?: string;
  nodes: ConceptDagNode[];
  edges: ConceptDagEdge[];
}

export interface StudentRewardsSummary {
  studentId: string;
  totalXp: number;
  xp?: number;
  coins?: number;
  zenithCoins: number;
  currentLevel: number;
  currentLevelProgressXp: number;
  xpToNextLevel: number;
  currentStreakDays: number;
  streak?: number;
  longestStreakDays?: number;
  lastActiveDate?: string | null;
  streakActiveToday?: boolean;
  timezone?: string;
  badges: Array<{
    id: string;
    name: string;
    description: string;
    category: string;
    iconUrl: string;
    awardedAt: string | null;
  }>;
  recentEvents?: Array<{
    eventType: string;
    xpAwarded: number;
    coinsAwarded: number;
    createdAt: string;
  }>;
}

export interface BadgeCatalogItem {
  id: string;
  name: string;
  description: string;
  category: string;
  iconUrl: string;
  xpBonus: number;
  isUnlocked: boolean;
  awardedAt: string | null;
}

export interface PracticeQuestion {
  questionId: string;
  conceptId: string;
  conceptTitle?: string;
  type?: string;
  prompt: string;
  options: string[];
  hints: string[];
  difficulty?: string;
}

export interface PracticeSessionResponse {
  chapterSlug: string;
  conceptId?: string | null;
  totalQuestions: number;
  questions: PracticeQuestion[];
}

export interface PracticeSubmitResponse {
  questionId: string;
  conceptId: string;
  isCorrect: boolean;
  feedback: string;
  explanation: string;
  pKnow: number;
  masteryBand: string;
  isGap: boolean;
  rewards: {
    awarded: boolean;
    xpAwarded: number;
    coinsAwarded: number;
    totalXp: number;
    currentStreak: number;
  };
}

export interface PracticeRecommendationResponse {
  conceptId: string;
  conceptTitle: string;
  pKnow: number;
  masteryBand: string;
  isGap: boolean;
  reason: string;
  chapterSlug: string;
}

export interface DiagnosticSessionItem {
  itemIndex: number;
  itemId: string;
  conceptId: string;
  probeType: 'chapter_core' | 'prerequisite_bridge';
  prompt: string;
  options: string[];
  difficulty?: string;
}

export interface DiagnosticSessionResponse {
  sessionId: string;
  chapterSlug: string;
  totalProbes: number;
  items: DiagnosticSessionItem[];
}

export interface DiagnosticSubmitResponse {
  sessionId: string;
  totalProbes: number;
  correctCount: number;
  accuracyPct: number;
  masteryUpdates: Record<string, { pKnow: number; masteryBand: string; isGap: boolean }>;
  gapSummary: {
    confirmedGaps: string[];
    gapCount: number;
  };
  recommendedPractice: {
    conceptId: string;
    conceptTitle: string;
    reason: string;
  };
  rewards: {
    xpAwarded: number;
    coinsAwarded: number;
    totalXp: number;
  };
}

export interface TutorCitation {
  id: number;
  source: string;
  excerpt: string;
}

export interface TutorMessageResponse {
  threadId: string;
  messageId: string;
  reply: string;
  citations: TutorCitation[];
  isDegraded: boolean;
  quotaExceeded: boolean;
}

export interface TutorThreadItem {
  id: string;
  title: string;
  conceptId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TutorMessageItem {
  id: string;
  sender: 'student' | 'assistant';
  content: string;
  citations: TutorCitation[];
  isDegraded: boolean;
  createdAt: string;
}

export const api = {
  // Auth
  async signup(data: { email: string; password: string; displayName: string; role?: string; grade?: number; boardId?: string; preferredLanguage?: string }): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async getMe(): Promise<{ user: UserProfileData }> {
    return request<{ user: UserProfileData }>('/auth/me');
  },

  // Profile
  async getProfile(): Promise<UserProfileData> {
    return request<UserProfileData>('/profile');
  },

  async updateProfile(updates: Partial<UserProfileData>): Promise<{ profile: UserProfileData }> {
    return request<{ profile: UserProfileData }>('/profile', {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  },

  // Catalogue
  async getBoards(): Promise<CatalogueBoard[]> {
    return request<CatalogueBoard[]>('/catalogue/boards');
  },

  async getSubjects(): Promise<CatalogueSubject[]> {
    return request<CatalogueSubject[]>('/catalogue/subjects');
  },

  async getLanguages(): Promise<CatalogueLanguage[]> {
    return request<CatalogueLanguage[]>('/catalogue/languages');
  },

  async getCatalogue(params?: { query?: string; grade?: number; subjectId?: string; boardId?: string }): Promise<CatalogueResource[]> {
    const q = new URLSearchParams();
    if (params?.query) q.append('search', params.query);
    if (params?.grade) q.append('grade', String(params.grade));
    if (params?.subjectId) q.append('subject_id', params.subjectId);
    if (params?.boardId) q.append('board_id', params.boardId);
    const queryString = q.toString() ? `?${q.toString()}` : '';
    const res = await request<any>(`/catalogue/resources${queryString}`);
    return Array.isArray(res) ? res : res.resources || [];
  },

  // Documents
  uploadDocument(
    file: File,
    onProgress?: (percent: number) => void,
    requestRef?: { current: XMLHttpRequest | null }
  ): Promise<{ documentId: string; filename: string; pageCount: number; chunkCount: number; status: string; errorMessage?: string; progressMessage?: string; deduplicated?: boolean }> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      if (requestRef) requestRef.current = xhr;
      xhr.open('POST', `${API_BASE}/documents/upload`);
      const token = localStorage.getItem('setu_auth_token');
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onload = () => {
        let body: any = {};
        try {
          body = JSON.parse(xhr.responseText || '{}');
        } catch {
          body = {};
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body);
          return;
        }
        const detail = body.detail || xhr.statusText || 'Upload failed.';
        reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)));
      };
      xhr.onerror = () => reject(new TypeError('Upload failed before the server stored the file.'));
      xhr.onabort = () => reject(new Error('Upload cancelled.'));
      const formData = new FormData();
      formData.append('file', file);
      xhr.send(formData);
    });
  },

  async listDocuments(): Promise<UserDocument[]> {
    const res = await request<UserDocument[] | { documents: UserDocument[] }>('/documents');
    return Array.isArray(res) ? res : res.documents || [];
  },

  async retryDocument(documentId: string): Promise<UserDocument> {
    return request<UserDocument>(`/documents/${documentId}/retry`, { method: 'POST' });
  },

  async getDocumentStatus(documentId: string): Promise<IngestionStatus> {
    return request<IngestionStatus>(`/documents/${documentId}/status`);
  },

  async deleteDocument(documentId: string): Promise<{ success: boolean; documentId: string }> {
    return request<{ success: boolean; documentId: string }>(`/documents/${documentId}`, {
      method: 'DELETE'
    });
  },

  // Learning Paths
  async getLearningPaths(): Promise<LearningPathItem[]> {
    const res = await request<LearningPathItem[] | { paths: LearningPathItem[] }>('/learning-paths');
    return Array.isArray(res) ? res : res.paths || [];
  },

  async createLearningPath(data: { documentId: string; grade: number; subjectId: string }): Promise<any> {
    return request<any>('/learning-paths', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async getLesson(lessonId: string): Promise<any> {
    return request<any>(`/learning-paths/lessons/${lessonId}`);
  },

  async submitAttempt(data: AttemptSubmission): Promise<AttemptResult> {
    return request<AttemptResult>('/attempts', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  // Doubts (Real online submission & history)
  async askDoubt(data: {
    questionText: string;
    pathId?: string;
    lessonVersionId?: string;
    blockId?: string;
    sourcePage?: number;
    clientDoubtId?: string;
  }): Promise<{ id: string; status: string; answerJson?: any }> {
    return request<{ id: string; status: string; answerJson?: any }>('/doubts', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async listDoubts(): Promise<Array<{
    id: string;
    clientDoubtId: string;
    status: string;
    questionText: string;
    answerJson?: any;
    lastErrorCode?: string | null;
    pathId?: string | null;
    lessonVersionId?: string | null;
    sourcePage?: number;
    blockId?: string;
    createdAt: string;
  }>> {
    const res = await request<any>('/doubts');
    return Array.isArray(res) ? res : res.doubts || [];
  },

  // Teacher & Classrooms
  async getClassrooms(): Promise<ClassroomData[]> {
    const res = await request<any>('/teacher/classrooms');
    return Array.isArray(res) ? res : res.classrooms || [];
  },

  async createClassroom(data: { name: string; grade: number; boardId: string; subjectScope: string }): Promise<ClassroomData> {
    return request<ClassroomData>('/teacher/classrooms', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async joinClassroom(joinCode: string): Promise<{ success: boolean; classroom: any; membership: any }> {
    return request<{ success: boolean; classroom: any; membership: any }>('/teacher/join', {
      method: 'POST',
      body: JSON.stringify({ joinCode })
    });
  },

  async getEvidenceMatrix(classroomId: string): Promise<EvidenceMatrixResponse> {
    return request<EvidenceMatrixResponse>(`/teacher/classrooms/${classroomId}/evidence-matrix`);
  },

  async getClassroomRoster(classroomId: string): Promise<{
    classroomId: string;
    joinCode: string | null;
    members: RosterMember[];
  }> {
    return request(`/teacher/classrooms/${classroomId}/roster`);
  },

  async rotateJoinCode(classroomId: string): Promise<{ classroomId: string; joinCode: string }> {
    return request(`/teacher/classrooms/${classroomId}/rotate-join-code`, { method: 'POST' });
  },

  async updateClassroomMember(
    classroomId: string,
    studentId: string,
    status: 'active' | 'removed'
  ): Promise<{ classroomId: string; studentId: string; status: string }> {
    return request(`/teacher/classrooms/${classroomId}/members/${studentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  async decideTeacherAction(
    actionId: string,
    decision: 'accept' | 'dismiss' | 'override',
    notes?: string
  ): Promise<{ id: string; status: string; decision: string; notes: string }> {
    return request(`/teacher/actions/${actionId}`, {
      method: 'PATCH',
      body: JSON.stringify({ decision, notes }),
    });
  },

  async addRecommendation(data: { classroomId: string; studentId: string; conceptId: string; actionType: string; notes: string }): Promise<{
    id: string;
    status: string;
    actionType: string;
    conceptId: string;
    notes: string;
    reason: {
      evidence?: EvidenceConceptRow;
      [key: string]: unknown;
    };
  }> {
    return request('/teacher/recommendations', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async respondToRecommendation(actionId: string, decision: 'accept' | 'dismiss'): Promise<{ id: string; status: string }> {
    return request(`/study/recommendations/${actionId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    });
  },

  async getStudySummary(): Promise<{
    minutesStudied: number;
    readingTitle?: string | null;
    checkpointCount: number;
    accuracyRate: number | null;
    improvement: string;
    pace: string | null;
    dailyGoalMinutes: number | null;
    focus: string;
    heatmap: Array<{ date: string; seconds: number }>;
    suggestions: Array<{
      id: string;
      note: string;
      actionType: string;
      conceptId?: string | null;
      status?: string;
      explanation?: string | null;
      teacherName?: string | null;
      createdAt?: string | null;
    }>;
  }> {
    return request('/study/summary');
  },

  async getLearnerInsights(): Promise<LearnerInsights> {
    return request<LearnerInsights>('/study/insights');
  },

  async getStudyPlan(): Promise<StudyPlan> {
    return request<StudyPlan>('/study/plan');
  },

  async fetchCoachNote(conceptId: string): Promise<CoachNoteResponse> {
    return request<CoachNoteResponse>(`/study/coach-note/${encodeURIComponent(conceptId)}`);
  },

  async myClassrooms(): Promise<MyClassroomEntry[]> {
    const res = await request<{ classrooms: MyClassroomEntry[] }>('/classroom/me');
    return res.classrooms || [];
  },

  async getClassroomMessages(classroomId: string, after?: string): Promise<ClassroomChatMessage[]> {
    const query = after ? `?after=${encodeURIComponent(after)}` : '';
    const res = await request<{ messages: ClassroomChatMessage[] }>(
      `/classroom/${classroomId}/messages${query}`
    );
    return res.messages || [];
  },

  async sendClassroomMessage(
    classroomId: string,
    data: { body: string; kind: 'group' | 'direct'; recipientId?: string }
  ): Promise<ClassroomChatMessage> {
    const res = await request<{ message: ClassroomChatMessage }>(
      `/classroom/${classroomId}/messages`,
      { method: 'POST', body: JSON.stringify(data) }
    );
    return res.message;
  },

  async getLessonCoaching(lessonId: string): Promise<LessonCoaching> {
    return request<LessonCoaching>(`/study/coach/${lessonId}`);
  },

  async getSmartCheck(): Promise<SmartCheckResponse> {
    return request<SmartCheckResponse>('/study/smart-check');
  },

  async getNextSmartQuestion(answeredQuestionKeys: string[]): Promise<SmartCheckNextResponse> {
    return request<SmartCheckNextResponse>('/study/smart-check/next', {
      method: 'POST',
      body: JSON.stringify({ answeredQuestionKeys }),
    });
  },

  async getStudentDashboard(): Promise<StudentDashboardResponse> {
    return request<StudentDashboardResponse>('/profile/dashboard');
  },

  async recordStudy(data: {
    eventType: 'reading' | 'checkpoint';
    pathId?: string;
    lessonId?: string;
    lessonTitle?: string;
    seconds?: number;
    score?: number;
  }): Promise<{ id: string }> {
    return request('/study/events', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  // -----------------------------------------------------------
  // ZENITH Curriculum, Rewards, Practice, Diagnostics & Tutor
  // -----------------------------------------------------------

  async getLibraryCatalogue(grade: number = 10, subjectId: string = 'subject-math'): Promise<LibraryCatalogueResponse> {
    return request<LibraryCatalogueResponse>(`/library/catalogue?grade=${grade}&subject_id=${encodeURIComponent(subjectId)}`);
  },

  async getChapter(slug: string): Promise<ChapterDetailResponse> {
    return request<ChapterDetailResponse>(`/library/chapters/${encodeURIComponent(slug)}`);
  },

  async getResource(resourceId: string): Promise<ResourcePackageResponse> {
    return request<ResourcePackageResponse>(`/library/resources/${encodeURIComponent(resourceId)}`);
  },

  async getConceptMap(slug: string): Promise<ConceptDagMapResponse> {
    return request<ConceptDagMapResponse>(`/library/map/${encodeURIComponent(slug)}`);
  },

  async enrollChapter(chapterSlug: string): Promise<{ success: boolean; chapterSlug: string }> {
    return request('/library/enroll', {
      method: 'POST',
      body: JSON.stringify({ chapter_slug: chapterSlug })
    });
  },

  async getMyLearning(): Promise<{ totalEnrolledChapters: number; totalCompletedResources: number; enrolledChapters: any[] }> {
    return request('/library/my');
  },

  async updateResourceProgress(payload: {
    pathLessonId: string;
    status: string;
    completionPct: number;
    timeSpentSeconds: number;
    lastPosition?: string;
  }): Promise<any> {
    return request('/library/progress', {
      method: 'POST',
      body: JSON.stringify({
        path_lesson_id: payload.pathLessonId,
        status: payload.status,
        completion_pct: payload.completionPct,
        time_spent_seconds: payload.timeSpentSeconds,
        last_position: payload.lastPosition
      })
    });
  },

  async getRewards(): Promise<StudentRewardsSummary> {
    return request<StudentRewardsSummary>('/rewards/me');
  },

  async getBadges(): Promise<{ badges: BadgeCatalogItem[] }> {
    return request<{ badges: BadgeCatalogItem[] }>('/rewards/badges');
  },

  async claimDailyLogin(): Promise<any> {
    return request('/rewards/claim-daily', { method: 'POST' });
  },

  async getPracticeRecommendation(chapterSlug: string): Promise<PracticeRecommendationResponse> {
    return request<PracticeRecommendationResponse>(`/practice/recommendation?chapter_slug=${encodeURIComponent(chapterSlug)}`);
  },

  async createPracticeSession(chapterSlug: string, conceptId?: string, count: number = 5): Promise<PracticeSessionResponse> {
    return request<PracticeSessionResponse>('/practice/session', {
      method: 'POST',
      body: JSON.stringify({
        chapter_slug: chapterSlug,
        concept_id: conceptId || null,
        count
      })
    });
  },

  async submitPracticeAttempt(payload: {
    questionId: string;
    conceptId: string;
    response: unknown;
    hintLevel?: number;
    hintsUsed?: string[] | number;
    elapsedSeconds?: number;
    syncIdempotencyKey?: string;
  }): Promise<PracticeSubmitResponse> {
    const hintsUsedList: string[] = Array.isArray(payload.hintsUsed)
      ? payload.hintsUsed
      : typeof payload.hintsUsed === 'number' && payload.hintsUsed > 0
      ? Array.from({ length: payload.hintsUsed }, (_, i) => `hint_${i + 1}`)
      : [];

    return request<PracticeSubmitResponse>('/practice/submit', {
      method: 'POST',
      body: JSON.stringify({
        question_id: payload.questionId,
        concept_id: payload.conceptId,
        response: payload.response,
        hint_level: payload.hintLevel ?? 0,
        hints_used: hintsUsedList,
        elapsed_seconds: payload.elapsedSeconds ?? 0,
        sync_idempotency_key: payload.syncIdempotencyKey
      })
    });
  },

  async startDiagnosticSession(chapterSlug: string): Promise<DiagnosticSessionResponse> {
    return request<DiagnosticSessionResponse>('/diagnostics/session', {
      method: 'POST',
      body: JSON.stringify({ chapter_slug: chapterSlug })
    });
  },

  async getDiagnosticSession(sessionId: string): Promise<DiagnosticSessionResponse> {
    return request<DiagnosticSessionResponse>(`/diagnostics/session/${encodeURIComponent(sessionId)}`);
  },

  async submitDiagnostic(sessionId: string, responses: any[]): Promise<DiagnosticSubmitResponse> {
    return request<DiagnosticSubmitResponse>('/diagnostics/submit', {
      method: 'POST',
      body: JSON.stringify({
        sessionId,
        responses
      })
    });
  },

  async sendTutorMessage(payload: {
    message: string;
    threadId?: string;
    chapterSlug?: string;
    resourceKey?: string;
    conceptId?: string;
    simulateProviderOffline?: boolean;
  }): Promise<TutorMessageResponse> {
    return request<TutorMessageResponse>('/tutor/message', {
      method: 'POST',
      body: JSON.stringify({
        message: payload.message,
        thread_id: payload.threadId || null,
        chapter_slug: payload.chapterSlug || null,
        resource_key: payload.resourceKey || null,
        concept_id: payload.conceptId || null,
        simulate_provider_offline: payload.simulateProviderOffline || false
      })
    });
  },

  async listTutorThreads(): Promise<TutorThreadItem[]> {
    return request<TutorThreadItem[]>('/tutor/threads');
  },

  async getTutorThreadMessages(threadId: string): Promise<TutorMessageItem[]> {
    return request<TutorMessageItem[]>(`/tutor/threads/${encodeURIComponent(threadId)}/messages`);
  }
};
