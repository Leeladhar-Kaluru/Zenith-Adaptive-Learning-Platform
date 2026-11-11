import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Band, EvidenceResult, NextPractice } from '../api/types';
import { useFx } from '../fx/fx';
import { Icon } from '../icons/Icon';
import { Question } from '../lesson/Question';
import { Button, Card, Chip, CountUp, EmptyState, Segmented, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const ROUND = 5;
const NAME: Record<Band, string> = { unassessed: 'Not enough answers yet', learning: 'Learning', secure: 'Secure', gap_suspected: 'Early signal: keep practising', gap_confirmed: 'Gap found: refresher recommended' };
const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { unassessed: 'soft', learning: 'hi', secure: 'ok', gap_suspected: 'hi', gap_confirmed: 'gap' };
const LEVEL = ['', 'Building', 'Growing', 'Challenge'];

export default function Practice() {
  const [q, setQ] = useSearchParams();
  const fx = useFx();
  const [cur, setCur] = useState<NextPractice | null>(null);
  const [n, setN] = useState(0);
  const [results, setResults] = useState<EvidenceResult[]>([]);
  const [answered, setAnswered] = useState(false);
  const [err, setErr] = useState<{ text: string; status: number } | null>(null);
  const [round, setRound] = useState(0);
  const celebrated = useRef(false);
  const harder = q.get('harder') === '1';
  const pattern = q.get('pattern') ?? '';
  const setPattern = (v: string) => { const p = new URLSearchParams(q); if (v) p.set('pattern', v); else p.delete('pattern'); setQ(p); };

  const load = useCallback(async () => {
    setErr(null); setCur(null); setAnswered(false);
    try { setCur(await api<NextPractice>(`/practice/next?${q.toString()}`)); }
    catch (e) { setErr({ text: (e as Error).message, status: (e as { status?: number }).status ?? 0 }); }
  }, [q]);
  useEffect(() => { void load(); }, [load, round]);

  const done = n >= ROUND;
  const right = results.filter((r) => r.correct).length;
  const xp = results.reduce((a, r) => a + r.xp, 0);
  useEffect(() => { if (done && right >= 4 && !celebrated.current) { celebrated.current = true; fx.confetti(); } }, [done, right, fx]);

  if (err) return <Card><EmptyState icon={err.status === 409 ? 'info' : 'wifiOff'} title={err.status === 409 ? 'Nothing to practise here yet' : 'Could not load a question'} text={err.text}
    action={err.status === 409 ? (pattern ? <Button variant="brand" onClick={() => setPattern('')}>Show all question types</Button> : <Button to="/learn" variant="brand">Browse Learn</Button>) : <Button onClick={() => setRound((r) => r + 1)} icon="refresh">Try again</Button>} /></Card>;

  if (done) {
    const concepts = new Map<string, EvidenceResult['concepts'][number]>();
    results.forEach((r) => r.concepts.forEach((c) => concepts.set(c.id, c)));
    const weak = [...concepts.values()].filter((c) => c.band === 'gap_suspected' || c.band === 'gap_confirmed');
    return (
      <div className={s.q}>
        <div><span className={s.tag}>Round complete</span><h1 className={s.title}>{right} of {ROUND} right</h1><p className={s.lead}>You earned <CountUp to={xp} /> XP. Here is what we noticed.</p></div>
        <Card><h3>Your topics</h3><div className={s.stack} style={{ marginTop: 12 }}>{[...concepts.values()].map((c) => (
          <div key={c.id} className={s.between}><div><strong>{c.title}</strong><div className="sm muted">{c.evidence} answer{c.evidence === 1 ? '' : 's'} so far · confidence {c.confidence}</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>
        ))}</div></Card>
        <Card flat style={{ background: 'var(--brand-soft)' }}><div className={s.row}><Icon name="compass" size={30} /><div style={{ flex: 1 }}>
          <strong>{weak.length ? 'Next: strengthen the basics' : right >= 4 ? 'Next: try harder questions' : 'Next: one more round'}</strong>
          <div className="sm muted">{weak.length ? `${weak[0].title} needs more work. Your Home screen will point to the right lesson.` : right >= 4 ? 'You are ready for more challenge.' : 'A little more practice will make this secure.'}</div></div></div></Card>
        <div className={s.row}>
          <Button variant="brand" icon="refresh" onClick={() => { setN(0); setResults([]); celebrated.current = false; setRound((r) => r + 1); }}>Another round</Button>
          {right >= 4 && !harder && <Button variant="ghost" icon="bolt" onClick={() => { const p = new URLSearchParams(q); p.set('harder', '1'); setQ(p); setN(0); setResults([]); celebrated.current = false; }}>Make it harder</Button>}
          <Button to="/home" variant="ghost">Back to Home</Button>
        </div>
      </div>
    );
  }

  return (
    <div className={s.q}>
      <div className={s.between}>
        <div><span className="eyebrow">Practice{cur ? ` · ${cur.concept.title}` : ''}</span><div className="muted sm">Question {n + 1} of {ROUND}</div></div>
        <div className={s.row}>{results.length > 0 && <Chip icon="check" tone="ok">{right} right</Chip>}{cur && <Chip tone="soft">{cur.generated ? `Level ${cur.ladderLevel} of 5` : LEVEL[cur.concept.level]} · {cur.item.difficulty === 'intro' ? 'Warm-up' : cur.item.difficulty === 'challenge' ? 'Challenge' : 'Standard'}</Chip>}</div>
      </div>
      <div className={s.steps} aria-hidden="true">{Array.from({ length: ROUND }, (_, i) => <i key={i} className={i < n ? s.on : ''} />)}</div>
      {n === 0 && !answered && <Segmented label="Question type" value={pattern} onChange={setPattern}
        options={[{ value: '', label: 'All' }, { value: 'mcq', label: 'Multiple choice' }, { value: 'assertion', label: 'Assertion and reason' }, { value: 'numeric', label: 'Numerical' }, { value: 'case', label: 'Case-based' }]} />}
      {!cur ? <div className={s.stack}><Skeleton h={40} w="70%" /><Skeleton h={60} r={14} /><Skeleton h={60} r={14} /><Skeleton h={60} r={14} /></div> : (
        <Card key={n}>
          <Question item={cur.item} context="solve" resetKey={n} onResult={(r) => { if (r) { setResults((x) => [...x, r]); setAnswered(true); } }} />
          <p className="sm muted" style={{ marginTop: 12 }}><Icon name="info" size={16} /> {cur.why}</p>
        </Card>
      )}
      {answered && <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button variant="brand" iconRight="arrowR" onClick={() => { setN((x) => x + 1); if (n + 1 < ROUND) void load(); }}>{n + 1 === ROUND ? 'See my plan' : 'Next question'}</Button></div>}
    </div>
  );
}
