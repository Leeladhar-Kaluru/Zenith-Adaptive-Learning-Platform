import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { Band, EvidenceResult, PublicItem } from '../api/types';
import { useFx } from '../fx/fx';
import { Icon } from '../icons/Icon';
import { Check } from '../lesson/Blocks';
import { Button, Card, Chip, CountUp, EmptyState, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const TOTAL = 5;
const BAND_LABEL: Record<Band, string> = { unassessed: 'Not enough answers yet', learning: 'Learning', secure: 'Secure', gap_suspected: 'Early signal: keep practising', gap_confirmed: 'Gap found: refresher recommended' };
const BAND_TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { unassessed: 'soft', learning: 'hi', secure: 'ok', gap_suspected: 'hi', gap_confirmed: 'gap' };

export default function Practice() {
  const fx = useFx();
  const [item, setItem] = useState<PublicItem | null>(null);
  const [n, setN] = useState(0);
  const [results, setResults] = useState<EvidenceResult[]>([]);
  const [answered, setAnswered] = useState(false);
  const [err, setErr] = useState('');
  const [run, setRun] = useState(0);
  const celebrated = useRef(false);

  const load = useCallback(async () => {
    setErr(''); setItem(null); setAnswered(false);
    try { setItem(await api<PublicItem>('/practice/next')); } catch (e) { setErr((e as Error).message); }
  }, []);
  useEffect(() => { void load(); }, [load, run]);

  const done = n >= TOTAL;
  const correct = results.filter((r) => r.correct).length;
  const xp = results.reduce((a, r) => a + r.xp, 0);
  useEffect(() => {
    if (done && correct >= 4 && !celebrated.current) { celebrated.current = true; fx.confetti(); }
  }, [done, correct, fx]);

  if (err) return <EmptyState icon="wifiOff" title="Could not load a question" text={err} action={<Button onClick={() => setRun((r) => r + 1)} icon="refresh">Try again</Button>} />;

  if (done) {
    const concepts = new Map<string, EvidenceResult['concept']>();
    results.forEach((r) => concepts.set(r.concept.id, r.concept));
    const weak = [...concepts.values()].filter((c) => c.band === 'gap_suspected' || c.band === 'gap_confirmed');
    return (
      <div className={s.q}>
        <div><span className={s.tag}>Round complete</span><h1 className={s.title}>{correct} of {TOTAL} right</h1><p className={s.lead}>You earned <CountUp to={xp} /> XP. Here is your plan.</p></div>
        <Card>
          <h3>What we noticed</h3>
          <div className={s.stack} style={{ marginTop: 12 }}>
            {[...concepts.values()].map((c) => <div key={c.id} className={s.between}><span style={{ fontWeight: 700 }}>{c.title}</span><Chip tone={BAND_TONE[c.band]}>{BAND_LABEL[c.band]}</Chip></div>)}
          </div>
        </Card>
        <Card flat style={{ background: 'var(--brand-soft)' }}>
          <div className={s.row}><Icon name="compass" size={30} />
            <div style={{ flex: 1 }}><strong>{weak.length ? 'Next: revisit the basics' : correct >= 4 ? 'Next: try something harder' : 'Next: one more round'}</strong>
              <div className="sm muted">{weak.length ? `Take the short refresher on ${weak[0].title}, then try again.` : correct >= 4 ? 'You are ready for challenge questions.' : 'A little more practice will make this secure.'}</div></div>
          </div>
        </Card>
        <div className={s.row}>
          <Button variant="brand" icon="refresh" onClick={() => { setN(0); setResults([]); celebrated.current = false; setRun((r) => r + 1); }}>Another round</Button>
          <Button to="/today" variant="ghost">Back to Today</Button>
        </div>
      </div>
    );
  }

  return (
    <div className={s.q}>
      <div className={s.between}>
        <div><span className="eyebrow">Practice</span><div className="muted sm">Question {n + 1} of {TOTAL}</div></div>
        <div className={s.row}>{results.length > 0 && <Chip icon="check" tone="ok">{correct} right</Chip>}{item && <Chip tone="soft">{item.difficulty === 'intro' ? 'Warm-up' : item.difficulty === 'challenge' ? 'Challenge' : 'Standard'}</Chip>}</div>
      </div>
      <div className={s.steps} aria-hidden="true">{Array.from({ length: TOTAL }, (_, i) => <i key={i} className={i < n ? s.on : ''} />)}</div>
      {!item ? <div className={s.stack}><Skeleton h={40} w="70%" /><Skeleton h={60} r={14} /><Skeleton h={60} r={14} /><Skeleton h={60} r={14} /></div> : (
        <Card key={n}>
          <Check item={item} context="solve" resetKey={n} onResult={(r) => { setResults((x) => [...x, r]); setAnswered(true); }} />
        </Card>
      )}
      {answered && <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button variant="brand" iconRight="arrowR" onClick={() => { setN((x) => x + 1); void load(); }}>{n + 1 === TOTAL ? 'See my plan' : 'Next question'}</Button></div>}
    </div>
  );
}
