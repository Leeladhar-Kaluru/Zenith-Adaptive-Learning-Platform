import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { PublicItem } from '../api/types';
import { Question } from '../lesson/Question';
import { Button, Card, Chip, EmptyState, Segmented, Skeleton } from '../ui/kit';
import { useApi } from '../api/useApi';
import s from './pages.module.css';

interface Step {
  model: string; answered: number; right: number; ability: number; se: number; interval: [number, number]; level: string; done: boolean; reason: string;
  item?: PublicItem; why?: string; topics?: Array<{ id: string; title: string; right: number; total: number; practice: string }>;
}

/** An adaptive check: each question is chosen from your earlier answers, and it stops as soon as ZENITH can estimate your level well enough. */
export default function AdaptiveCheck() {
  const [q] = useSearchParams();
  const [subject, setSubject] = useState(q.get('subject') ?? '');
  const subjects = useApi<Array<{ id: string; name: string; questions: number }>>('/practice/subjects');
  const [since, setSince] = useState<string | null>(null);
  const [step, setStep] = useState<Step | null>(null);
  const [err, setErr] = useState<{ text: string; status: number } | null>(null);
  const [answered, setAnswered] = useState(false);
  const started = useRef(false);

  const scope = new URLSearchParams();
  for (const k of ['chapter', 'concept']) if (q.get(k)) scope.set(k, q.get(k)!);
  if (subject) scope.set('subject', subject);

  const load = useCallback(async (from: string) => {
    setErr(null); setAnswered(false); setStep(null);
    try { setStep(await api<Step>(`/adaptive/step?${new URLSearchParams({ since: from, ...Object.fromEntries(scope) }).toString()}`)); }
    catch (e) { setErr({ text: (e as Error).message, status: (e as { status?: number }).status ?? 0 }); }
  }, [scope.toString()]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = () => { const t = new Date(Date.now() - 1000).toISOString(); setSince(t); started.current = true; void load(t); };
  useEffect(() => { /* the check starts only when the student presses Start, so nothing is recorded by opening the page */ }, []);

  if (!since) {
    return (
      <div className={s.stack}>
        <div><h1 className={s.title}>Adaptive check</h1><p className={s.lead}>A short check of 6 to 12 questions. Each question depends on how you answered before, and it stops as soon as ZENITH can tell your level. The answers count in your profile like any other practice.</p></div>
        {subjects.data && subjects.data.length > 0 && !q.get('concept') && !q.get('chapter') && <Segmented label="Subject" value={subject} onChange={setSubject} options={[{ value: '', label: 'All subjects' }, ...subjects.data.map((x) => ({ value: x.id, label: x.name }))]} />}
        <div><Button variant="brand" icon="spark" onClick={start}>Start the check</Button></div>
      </div>
    );
  }
  if (err) return <Card><EmptyState icon={err.status === 409 ? 'info' : 'wifiOff'} title={err.status === 409 ? 'Nothing to check here yet' : 'Could not load a question'} text={err.text} action={<Button onClick={() => void load(since)} icon="refresh">Try again</Button>} /></Card>;
  if (!step) return <div className={s.stack}><Skeleton h={40} w="70%" /><Skeleton h={60} r={14} /><Skeleton h={60} r={14} /></div>;

  if (step.done) {
    return (
      <div className={s.stack}>
        <div><span className="eyebrow">Check complete</span><h1 className={s.title}>You are {step.level}</h1><p className={s.lead}>{step.right} of {step.answered} right. {step.reason}</p></div>
        <Card><h3>How sure are we?</h3>
          <p className="muted sm" style={{ marginTop: 6 }}>Your estimated level is {step.ability.toFixed(1)}, and we are 90 % sure it is between {step.interval[0].toFixed(1)} and {step.interval[1].toFixed(1)}. On this scale 0 is a typical standard question. More answers make the range narrower.</p></Card>
        {step.topics && <Card><h3>By topic</h3><div className={s.stack} style={{ marginTop: 10 }}>{step.topics.map((t) => <div key={t.id} className={s.between}><div><strong>{t.title}</strong><div className="sm muted">{t.right} of {t.total} right</div></div><Button to={t.practice} size="sm" variant="ghost">Practise</Button></div>)}</div></Card>}
        <div className={s.row}><Button variant="brand" icon="refresh" onClick={start}>Check again</Button><Button to="/progress" variant="ghost">Back to my profile</Button></div>
      </div>
    );
  }
  return (
    <div className={s.q}>
      <div className={s.between}><div><span className="eyebrow">Adaptive check</span><div className="muted sm">Question {step.answered + 1}</div></div>
        <Chip tone="soft">Right so far: {step.right}</Chip></div>
      {step.item && <Card key={step.item.id}><Question item={step.item} context="probe" resetKey={step.item.id} onResult={(r) => { if (r) setAnswered(true); }} />
        <p className="sm muted" style={{ marginTop: 12 }}>{step.why}</p></Card>}
      {answered && <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button variant="brand" iconRight="arrowR" onClick={() => void load(since)}>Next</Button></div>}
    </div>
  );
}
