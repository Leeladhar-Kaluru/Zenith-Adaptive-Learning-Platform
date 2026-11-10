import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { TestSession } from '../../api/types';
import { RouteLoader } from '../../fx/fx';
import { Button, Card, EmptyState } from '../../ui/kit';
import s from '../pages.module.css';

const COPY: Record<string, string> = {
  diagnostic: 'A quick check to see where you are. It is not graded and it never counts against you.',
  chapter_test: 'Questions from across the chapter. You see how you did on each topic at the end.',
  topic_test: 'A short test on one topic.',
  revision: 'Questions on topics that are due for revision.',
};

export default function Start() {
  const [q] = useSearchParams();
  const nav = useNavigate();
  const kind = q.get('kind') ?? 'diagnostic';
  const [timed, setTimed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const auto = useRef(false);

  async function go() {
    setBusy(true); setErr('');
    try {
      const sess = await api<TestSession>('/assessments', { method: 'POST', body: { kind, chapter: q.get('chapter') || undefined, concept: q.get('concept') || undefined, timed, assignmentId: q.get('assignment') || undefined } });
      nav(`/tests/${sess.id}`, { replace: true });
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  }
  useEffect(() => { if (kind === 'diagnostic' && !auto.current) { auto.current = true; void go(); } }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (busy && kind === 'diagnostic') return <RouteLoader label="Choosing your questions" />;
  return (
    <div className={s.q}>
      {err ? <EmptyState icon="warn" title="Could not start" text={err} action={<Button to="/learn" variant="ghost">Back to Learn</Button>} /> : (
        <Card>
          <span className={s.tag}>{kind.replace('_', ' ')}</span><h1 style={{ fontSize: '2rem' }}>Ready?</h1><p className="muted" style={{ margin: '8px 0 16px' }}>{COPY[kind] ?? ''}</p>
          <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontWeight: 700, marginBottom: 16 }}><input type="checkbox" checked={timed} onChange={(e) => setTimed(e.target.checked)} style={{ width: 22, height: 22, accentColor: 'var(--brand)' }} />Timed (about 90 seconds a question)</label>
          <Button variant="brand" loading={busy} onClick={go} iconRight="arrowR">Start</Button>
        </Card>
      )}
    </div>
  );
}
