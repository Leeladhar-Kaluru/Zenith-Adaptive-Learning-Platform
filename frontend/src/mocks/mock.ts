// DEV-ONLY fixtures so every screen can be designed and checked before the backend ships.
// Loaded via dynamic import behind `import.meta.env.DEV`; never part of production bundles.
import type {
  Band, Chapter, ChapterDetail, Climb, ClassOverview, Lesson, MapGraph, Profile, ReviewDetail, ReviewQueueItem,
  StudentDetail, Today, TutorReply, EvidenceResult, PublicItem, Block,
} from '../api/types';

const delay = (ms = 220) => new Promise((r) => setTimeout(r, ms));
const me: Profile = { id: 'u1', displayName: 'Aarav K', nickname: 'Kiwi', avatar: 'fox', role: 'student', grade: 7, boardId: 'cbse', language: 'en', onboardingCompleted: true, consentStatus: 'granted', classroomIds: ['c1'] };

const chapters = (grade: number, subject: string): Chapter[] => [
  { id: `${grade}-${subject}-1`, slug: `${grade}-${subject}-integers`, grade, subject: subject as 'maths', number: 1, title: subject === 'maths' ? 'Integers' : 'Nutrition in Plants', status: 'published', lessonCount: 6, conceptCount: 14, progress: { done: 2, total: 6 } },
  { id: `${grade}-${subject}-2`, slug: `${grade}-${subject}-expressions`, grade, subject: subject as 'maths', number: 2, title: subject === 'maths' ? 'Algebraic Expressions' : 'Nutrition in Animals', status: 'published', lessonCount: 5, conceptCount: 11, progress: { done: 0, total: 5 } },
  { id: `${grade}-${subject}-3`, slug: `${grade}-${subject}-soon1`, grade, subject: subject as 'maths', number: 3, title: subject === 'maths' ? 'Simple Equations' : 'Heat', status: 'coming_soon', lessonCount: 0, conceptCount: 0, progress: null },
  { id: `${grade}-${subject}-4`, slug: `${grade}-${subject}-soon2`, grade, subject: subject as 'maths', number: 4, title: subject === 'maths' ? 'Triangles' : 'Acids, Bases and Salts', status: 'coming_soon', lessonCount: 0, conceptCount: 0, progress: null },
];

const item = (id: string, stem: string, opts: string[], difficulty: PublicItem['difficulty'] = 'standard'): PublicItem => ({
  id, stem, difficulty, hintCount: 2, options: opts.map((t, i) => ({ key: 'ABCD'[i], text: t })),
});
const KEY: Record<string, { key: string; why: string; mis?: string }> = {
  q1: { key: 'B', why: 'Subtracting walks left: 2 − 5 lands at −3.', mis: 'Treating 2 − 5 as 5 − 2' },
  q2: { key: 'C', why: '−3 + 5: start at −3, move 5 right, land on 2.' },
  q3: { key: 'A', why: '−4 is left of −1, so −4 is smaller.' },
  q4: { key: 'D', why: 'Adding a negative number moves you left.' },
};
const nlSvg = '<svg viewBox="0 0 320 90" role="img"><line x1="10" y1="50" x2="310" y2="50" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><g font-size="14" font-weight="700" text-anchor="middle" fill="currentColor"><text x="40" y="78">−3</text><text x="100" y="78">−2</text><text x="160" y="78">0</text><text x="220" y="78">2</text><text x="280" y="78">4</text></g><path d="M220 38C180 0 100 0 62 38" fill="none" stroke="#3a46d6" stroke-width="4" stroke-dasharray="2 9" stroke-linecap="round"/><circle cx="220" cy="50" r="8" fill="#ffd43b" stroke="#14193a" stroke-width="3"/><circle cx="62" cy="50" r="8" fill="#3a46d6" stroke="#14193a" stroke-width="3"/></svg>';

const blocks = (): Block[] => [
  { id: 'b1', kind: 'text', heading: 'Subtracting walks you left', html: '<p>On a <strong>number line</strong>, adding moves you to the right and subtracting moves you to the left. Start at 2 and take 5 steps left.</p>' },
  { id: 'b2', kind: 'widget', widget: 'numberline', config: { start: 2, min: -6, max: 6 } },
  { id: 'b3', kind: 'callout', tone: 'watch', html: '<strong>2 − 5 is not 3.</strong> The answer lands <em>left</em> of zero.' },
  { id: 'b4', kind: 'figure', svg: nlSvg, alt: 'A number line showing a jump from 2 to minus 3', caption: '2 − 5 = −3: five steps left from 2.' },
  { id: 'b5', kind: 'example', heading: 'Worked example', prompt: 'Work out −3 + 5.', steps: ['Start at −3 on the line.', 'Adding means move right. Take 5 steps right.', 'You pass 0 after 3 steps, then 2 more: you land on 2.'] },
  { id: 'b6', kind: 'check', item: item('q1', 'What is 2 − 5?', ['3', '−3', '−7']) },
  { id: 'b7', kind: 'callout', tone: 'real', html: 'Temperature drops 5 degrees from 2°C: it is now <strong>−3°C</strong>. Cold mornings in hill towns work just like this.' },
  { id: 'b8', kind: 'summary', points: ['Add: move right. Subtract: move left.', 'Crossing zero changes the sign.', 'Always sketch a quick number line when unsure.'] },
];

const lessonStubs = [
  { id: 'l1', title: 'Numbers below zero', order: 1, minutes: 8, state: 'done' as const },
  { id: 'l2', title: 'Comparing integers', order: 2, minutes: 8, state: 'done' as const },
  { id: 'l3', title: 'Moving on the line', order: 3, minutes: 12, state: 'current' as const },
  { id: 'l4', title: 'Adding integers', order: 4, minutes: 10, state: 'todo' as const },
  { id: 'l5', title: 'Subtracting integers', order: 5, minutes: 10, state: 'todo' as const },
  { id: 'l6', title: 'Word problems', order: 6, minutes: 12, state: 'todo' as const },
];
const gap = { conceptId: 'c6-count-back', title: 'Counting backwards past zero', grade: 6, lessonId: 'l0', band: 'gap_confirmed' as Band };
const lesson = (id: string): Lesson => ({ id, chapterSlug: '7-maths-integers', chapterTitle: 'Integers', subject: 'maths', title: 'Moving on the line', order: 3, total: 6, minutes: 12, prevId: 'l2', nextId: 'l4', prereqGap: gap, blocks: blocks(), siblings: lessonStubs });

const bands: Band[] = ['secure', 'learning', 'gap_confirmed', 'unassessed'];
const names: Array<[string, string]> = [['Kiwi', 'fox'], ['Panda', 'panda'], ['Owl', 'owl'], ['Turtle', 'turtle'], ['Comet', 'rocket'], ['Mochi', 'cat'], ['Bruno', 'bear'], ['Hopper', 'rabbit']];
const concepts = ['Integers', 'Expressions', 'Like terms', 'Equations', 'Word problems', 'Graphs'];
const heat = () => ({
  concepts: concepts.map((t, i) => ({ id: `k${i}`, title: t })),
  students: names.map(([nickname, avatar], i) => ({ id: `s${i}`, nickname, avatar, cells: concepts.map((_, j) => bands[(i * 3 + j * 5 + (j > 3 ? 3 : 0)) % bands.length] as Band) })),
});

const resolve = (path: string, init: { method?: string; body?: unknown }): unknown => {
  const u = new URL(path, 'http://x');
  const p = u.pathname;
  if (p === '/progress') return { ok: true };
  if (p === '/profile' && init.method === 'PUT') return { ...me, ...(init.body as object) };
  if (p === '/profile' || p === '/auth/me') return me;
  if (p === '/auth/login' || p === '/auth/signup') return { token: 'mock', profile: me };
  if (p === '/library/chapters') return chapters(Number(u.searchParams.get('grade') ?? 7), u.searchParams.get('subject') ?? 'maths');
  if (p.startsWith('/library/chapters/')) {
    const slug = p.split('/')[3];
    const ch = chapters(7, 'maths').find((c) => c.slug === slug) ?? chapters(7, 'maths')[0];
    return { chapter: ch, summary: 'Numbers on both sides of zero: compare them, move on the line, add and subtract.', lessons: lessonStubs, prerequisites: [gap, { conceptId: 'c6-order', title: 'Ordering whole numbers', grade: 6, lessonId: null, band: 'secure' }] } satisfies ChapterDetail;
  }
  if (p.startsWith('/library/lessons/')) return lesson(p.split('/')[3]);
  if (p === '/today') return { nextStep: { kind: 'prereq', title: 'Counting backwards past zero', reason: 'You missed 2 of 3 questions on −3 + 5. This 5-minute refresher builds the idea first.', minutes: 5, href: '/learn/lesson/l0', evidenceCount: 3 }, streak: 6, xp: 240, level: 3, levelProgress: 62, assigned: [{ id: 'a1', title: 'Integers: practice set', due: 'Friday', done: 2, total: 5, href: '/practice?set=a1' }], recent: [{ chapter: 'Integers', lesson: 'Moving on the line', href: '/learn/lesson/l3', progress: 40 }] } satisfies Today;
  if (p === '/practice/next') return item('q' + (1 + Math.floor(Math.random() * 4)), ['What is 2 − 5?', 'What is −3 + 5?', 'Which is smaller: −4 or −1?', 'What is 4 + (−6)?'][Math.floor(Math.random() * 4)], ['3', '−3', '2', '−2'], 'standard');
  if (p === '/evidence' && init.method === 'POST') {
    const b = init.body as { itemId: string; choice: string };
    const k = KEY[b.itemId] ?? KEY.q1;
    const correct = b.choice === k.key;
    return { correct, correctKey: k.key, feedback: correct ? k.why : `Not quite. ${k.why}`, misconception: correct ? null : k.mis ?? null, xp: correct ? 10 : 2, concept: { id: 'c7-int', title: 'Integers on the number line', band: correct ? 'learning' : 'gap_suspected' }, next: null } satisfies EvidenceResult;
  }
  if (p === '/climb') return { league: { tier: 'ridge', endsAt: new Date(Date.now() + 3 * 864e5).toISOString(), rows: names.slice(0, 6).map(([nickname, avatar], i) => ({ rank: i + 1, nickname, avatar, xp: 320 - i * 48, me: i === 2, zone: i < 2 ? 'up' : i > 4 ? 'down' : 'stay' })) }, leagueDisabledReason: null, quests: [{ id: 'q1', title: 'Fix one weak concept', icon: 'target', done: 1, total: 1 }, { id: 'q2', title: '3 correct in a row', icon: 'link', done: 2, total: 3 }, { id: 'q3', title: 'Finish a lesson', icon: 'book', done: 0, total: 1 }], goal: { title: '80% of us secure on Integers by Friday', percent: 62 }, badges: [{ id: 'b1', title: 'First step', hint: 'Answer your first question', icon: 'flag', earned: true }, { id: 'b2', title: 'Comeback', hint: 'Get one right after three misses', icon: 'arrowUp', earned: true }, { id: 'b3', title: 'Sharp shooter', hint: '5 correct in a row', icon: 'target', earned: false }, { id: 'b4', title: 'Chapter climber', hint: 'Finish every lesson in a chapter', icon: 'peak', earned: false }, { id: 'b5', title: 'Seven-day summit', hint: 'Keep a 7-day streak', icon: 'flame', earned: false }], streak: { days: 6, restDayAvailable: true } } satisfies Climb;
  if (p.startsWith('/map/')) return { chapterSlug: p.split('/')[2], nodes: [{ id: 'a', title: 'Counting backwards', grade: 6, band: 'gap_confirmed', x: 14, y: 70 }, { id: 'b', title: 'Number line', grade: 6, band: 'secure', x: 14, y: 25 }, { id: 'c', title: 'Comparing integers', grade: 7, band: 'secure', x: 42, y: 25 }, { id: 'd', title: 'Adding integers', grade: 7, band: 'learning', x: 58, y: 70 }, { id: 'e', title: 'Expressions', grade: 7, band: 'unassessed', x: 84, y: 40 }], edges: [['b', 'c'], ['a', 'd'], ['c', 'd'], ['d', 'e']] } satisfies MapGraph;
  if (p === '/tutor/ask') return { reply: 'Think of the number line as a street. Adding walks you one way, subtracting walks you back. If you start at 2 and walk 5 steps back, where do you cross zero?', citations: [{ title: 'Integers', heading: 'Subtracting walks you left' }], language: (init.body as { language?: string })?.language ?? 'en', aiTranslated: false, degraded: false } satisfies TutorReply;
  if (p === '/teacher/classes') return [{ id: 'c1', name: 'Class 7B', grade: 7, subject: 'maths', students: 8, joinCode: 'ZEN-4K7P' }];
  if (p.startsWith('/teacher/classes/')) return { cls: { id: 'c1', name: 'Class 7B', grade: 7, subject: 'maths', students: 8, joinCode: 'ZEN-4K7P' }, heatmap: heat(), recommendations: [{ id: 'r1', text: '3 students repeatedly missed negative-integer questions inside linear-equation problems.', evidence: '31 answers over 9 days', students: 3, lessonId: 'l5', lessonTitle: 'Subtracting integers' }], needsHelp: [{ id: 's2', nickname: 'Owl', avatar: 'owl', reason: 'Gap confirmed: counting backwards past zero' }, { id: 's5', nickname: 'Mochi', avatar: 'cat', reason: 'Learning stalled on adding integers' }] } satisfies ClassOverview;
  if (p.startsWith('/teacher/students/')) return { id: 's2', nickname: 'Owl', avatar: 'owl', grade: 7, concepts: [{ id: 'k0', title: 'Integers', band: 'gap_confirmed', evidenceCount: 7 }, { id: 'k1', title: 'Expressions', band: 'learning', evidenceCount: 4 }, { id: 'k3', title: 'Equations', band: 'unassessed', evidenceCount: 0 }], timeline: [{ at: 'Today 4:12 pm', text: 'Missed −3 + 5 (chose −8)' }, { at: 'Today 4:10 pm', text: 'Used 2 hints on 2 − 5' }, { at: 'Yesterday', text: 'Finished lesson: Comparing integers' }], interventions: [{ concept: 'Counting backwards past zero', before: 'gap_confirmed', after: null, status: 'open' }] } satisfies StudentDetail;
  if (p.startsWith('/review/lessons/') && init.method === 'POST') return { ok: true };
  if (p === '/teacher/assign' || (p === '/teacher/classes' && init.method === 'POST')) return { ok: true, id: 'c2' };
  if (p === '/review/queue') return [{ id: 'l3', title: 'Moving on the line', chapter: 'Class 7 · Integers', grade: 7, subject: 'maths', status: 'in_review', gates: { passed: 7, total: 8 }, origin: 'ai_assisted' }, { id: 'l4', title: 'Adding integers', chapter: 'Class 7 · Integers', grade: 7, subject: 'maths', status: 'in_review', gates: { passed: 8, total: 8 }, origin: 'ai_assisted' }, { id: 'l9', title: 'Like terms', chapter: 'Class 7 · Algebraic Expressions', grade: 7, subject: 'maths', status: 'changes_requested', gates: { passed: 6, total: 8 }, origin: 'human' }] satisfies ReviewQueueItem[];
  if (p.startsWith('/review/lessons/')) return { id: 'l3', title: 'Moving on the line', chapter: 'Class 7 · Integers', origin: 'ai_assisted', gates: [{ name: 'Schema valid', passed: true, detail: 'All required fields present' }, { name: 'Answers verified (SymPy)', passed: true, detail: '5 of 5 items check out' }, { name: 'One correct option per item', passed: true, detail: '' }, { name: 'Readability for Class 7', passed: true, detail: 'Grade level 6.4' }, { name: 'Maths notation parses', passed: true, detail: '' }, { name: 'Figures have alt text', passed: true, detail: '1 figure' }, { name: 'Prerequisites acyclic', passed: true, detail: '' }, { name: 'Curriculum mapping confirmed', passed: false, manual: true, detail: 'Chapter number not confirmed against NCERT 2025-26' }], flags: [{ id: 'f1', severity: 'warn', text: 'AI reviewer: the real-life example mentions °C; check students have met temperature scales.' }, { id: 'f2', severity: 'info', text: 'AI reviewer: consider a second worked example with a bigger jump.' }], lesson: lesson('l3') } satisfies ReviewDetail;
  throw new Error(`mock: unhandled ${p}`);
};

export async function mockFetch<T>(path: string, init: { method?: string; body?: unknown }): Promise<T> {
  await delay();
  return resolve(path, init) as T;
}
