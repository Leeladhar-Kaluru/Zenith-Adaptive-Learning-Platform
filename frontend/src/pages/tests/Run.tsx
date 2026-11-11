import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { clearApiCache, useApi, emitProgress } from '../../api/useApi';
import type { Band, TestSession, TestSummary } from '../../api/types';
import { useFx } from '../../fx/fx';
import { Icon } from '../../icons/Icon';
import { Question } from '../../lesson/Question';
import { Button, Card, Chip, CountUp, EmptyState, Skeleton, useToast } from '../../ui/kit';
import { pw } from '../../ui/powers';
import s from '../pages.module.css';

const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { secure: 'ok', learning: 'hi', gap_confirmed: 'gap', gap_suspected: 'hi', unassessed: 'soft' };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough answers yet' };
const mmss = (n: number) => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`;

function Results({ r, session }: { r: TestSummary; session: TestSession }) {
  const nav = useNavigate();
  const fx = useFx();
  useEffect(() => { if (r.accuracy >= 0.8) fx.confetti(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className={s.q}>
      <div><span className={s.tag}>Results</span><h1 className={s.title}><CountUp to={r.right} /> of {r.total} right</h1>{r.boss && <Chip tone={r.passed ? 'ok' : 'hi'}>{r.passed ? 'Boss beaten' : `Not yet. You need ${Math.round((r.passMark ?? 0.75) * 100)} percent`}</Chip>}<p className={s.lead}>{r.answered < r.total ? `${r.total - r.answered} question${r.total - r.answered === 1 ? ' was' : 's were'} not answered. ` : ''}{r.note}</p></div>
      <Card><h3>By topic</h3><div className={s.stack} style={{ marginTop: 12 }}>{r.byConcept.map((c) => (
        <div key={c.conceptId} className={s.between}><div><strong>{c.title}</strong><div className="sm muted">{c.right} of {c.total} in this test · {c.evidence} answers in total · confidence {c.confidence}</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>
      ))}</div></Card>
      {r.suggestions.length > 0 && <Card flat style={{ background: 'var(--brand-soft)' }}><h3>What to do next</h3><div className={s.stack} style={{ marginTop: 12 }}>{r.suggestions.map((x) => (
        <div key={x.conceptId} className={s.between}><div><strong>{x.action === 'prerequisite' ? `Start with the basics under ${x.title}` : `Revisit ${x.title}`}</strong><div className="sm muted">{x.why}</div></div><Button to={x.href} size="sm" variant="ghost" iconRight="arrowR">Open</Button></div>
      ))}</div></Card>}
      {r.mistakes.length > 0 && <section><h2 style={{ marginBottom: 12 }}>Mistake review</h2><div className={s.stack}>{r.mistakes.map((m) => (
        <Card key={m.itemId} flat><strong>{pw(m.stem)}</strong>{!m.answered && <Chip tone="soft">Not answered</Chip>}{m.misconception && <p className="sm" style={{ marginTop: 6 }}><strong>Common mistake:</strong> {m.misconception}</p>}<p className="sm muted" style={{ marginTop: 6 }}>{m.explanation}</p></Card>
      ))}</div></section>}
      <div className={s.row}><Button variant="brand" icon="refresh" onClick={() => nav(`/tests/new?kind=${session.kind}${session.chapter ? `&chapter=${session.chapter}` : ''}${session.conceptId ? `&concept=${session.conceptId}` : ''}`)}>Retake with new questions</Button><Button to="/progress" variant="ghost">My Progress</Button></div>
    </div>
  );
}

export default function Run() {
  const { id = '' } = useParams();
  const toast = useToast();
  const { data, error, loading, reload, setData } = useApi<TestSession>(`/assessments/${id}`);
  const [i, setI] = useState(0);
  const [left, setLeft] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [answered, setAnswered] = useState<Set<string>>(new Set());
  const submitted = useRef(false);

  useEffect(() => { if (data?.status === 'active') { setLeft(data.remainingS ?? null); setAnswered(new Set(data.answered ?? [])); setI(Math.min((data.answered ?? []).length, (data.items?.length ?? 1) - 1)); } }, [data?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (left === null || data?.status !== 'active') return;
    if (left <= 0) { void finish(); return; }
    const t = setTimeout(() => setLeft((x) => (x === null ? x : x - 1)), 1000);
    return () => clearTimeout(t);
  }, [left]); // eslint-disable-line react-hooks/exhaustive-deps

  async function finish() {
    if (submitted.current) return;
    submitted.current = true; setBusy(true);
    try { const out = await api<TestSession>(`/assessments/${id}/submit`, { method: 'POST' }); clearApiCache(); setData(out); emitProgress(); }
    catch (e) { submitted.current = false; toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  if (loading && !data) return <Skeleton h={320} r={16} />;
  if (error && !data) return <EmptyState icon="warn" title="Could not open this test" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  if (data.status !== 'active' && data.summary) return <Results r={data.summary} session={data} />;
  const items = data.items ?? [];
  const item = items[i];
  const all = answered.size >= items.length;

  return (
    <div className={s.q}>
      <div className={s.between}><div><span className="eyebrow">{data.kind.replace('_', ' ')}</span><div className="muted sm">Question {i + 1} of {items.length}</div></div>
        {left !== null && <Chip tone={left < 30 ? 'gap' : 'soft'} icon="clock">{mmss(Math.max(0, left))}</Chip>}</div>
      <div className={s.steps} aria-hidden="true">{items.map((x, k) => <i key={x.id} className={answered.has(x.id) ? s.on : k === i ? s.on : ''} />)}</div>
      {item && <Card key={item.id}><Question item={item} context="test" sessionId={id} deferFeedback onResult={() => setAnswered((a) => new Set(a).add(item.id))} resetKey={item.id} />
        {answered.has(item.id) && <p className="sm muted" style={{ marginTop: 10 }}><Icon name="info" size={16} /> Answers are shown when you finish the test.</p>}</Card>}
      <div className={s.between}>
        <Button variant="ghost" size="sm" icon="arrowL" disabled={i === 0} onClick={() => setI(i - 1)}>Back</Button>
        {i < items.length - 1 ? <Button variant="ghost" size="sm" iconRight="arrowR" onClick={() => setI(i + 1)}>{answered.has(item.id) ? 'Next' : 'Skip'}</Button> : <span />}
        <Button variant="brand" loading={busy} onClick={() => void finish()} icon="check" disabled={answered.size === 0}>{all ? 'Finish test' : `Finish (${items.length - answered.size} unanswered)`}</Button>
      </div>
    </div>
  );
}
