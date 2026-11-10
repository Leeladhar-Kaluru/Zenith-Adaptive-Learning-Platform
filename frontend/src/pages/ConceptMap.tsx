import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import type { Band, MapGraph } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const FILL: Record<Band, string> = { secure: 'var(--ok)', learning: 'var(--hi)', gap_confirmed: 'var(--gap)', gap_suspected: 'var(--retry)', unassessed: 'var(--surface-2)' };
const LABEL: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough answers yet' };

export default function MapPage() {
  const { slug = '' } = useParams();
  const { data, error, loading, reload } = useApi<MapGraph>(`/library/map/${slug}`);
  const [pick, setPick] = useState<string | null>(null);
  if (loading && !data) return <Skeleton h={420} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load the map" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const by = new Map(data.nodes.map((n) => [n.id, n]));
  const sel = pick ? by.get(pick) : null;

  return (
    <div className={s.stack}>
      <div>
        <Link to={`/learn/${slug}`} className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />Back to chapter</Link>
        <h1 className={s.title} style={{ marginTop: 6 }}>Concept map</h1>
        <p className={s.lead}>Arrows point from what you need first to what builds on it. Tap an idea to see where you stand.</p>
      </div>
      <Card>
        <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" style={{ width: '100%', height: 'min(62vh, 460px)' }} role="img" aria-label="Concept map of prerequisites">
          <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--ink)" /></marker></defs>
          {data.edges.map(([a, b], i) => { const A = by.get(a), B = by.get(b); if (!A || !B) return null; return <path key={i} d={`M${A.x} ${A.y} C ${(A.x + B.x) / 2} ${A.y}, ${(A.x + B.x) / 2} ${B.y}, ${B.x} ${B.y}`} fill="none" stroke="var(--ink)" strokeWidth=".6" strokeDasharray={A.band === 'gap_confirmed' ? '1.5 1.5' : undefined} markerEnd="url(#ah)" style={{ strokeDashoffset: 0 }} />; })}
          {data.nodes.map((n) => (
            <g key={n.id} onClick={() => setPick(n.id)} style={{ cursor: 'pointer' }} tabIndex={0} role="button" aria-label={`${n.title}, ${LABEL[n.band]}, mastery ${Math.round(n.mastery * 100)} percent${n.nextUnlock ? ', ready to learn next' : ''}`} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setPick(n.id)}>
              {n.nextUnlock && <circle cx={n.x} cy={n.y} r={8.2} fill="none" stroke="var(--brand)" strokeWidth=".7" strokeDasharray="1.6 1.2"><title>Ready to learn next</title></circle>}
              <circle cx={n.x} cy={n.y} r={pick === n.id ? 6.4 : 5.4} fill={FILL[n.band]} stroke="var(--ink)" strokeWidth=".8" style={{ transition: 'r .25s var(--spring)' }} />
              <circle cx={n.x} cy={n.y} r={7} fill="none" stroke="var(--ok)" strokeWidth="1.1" strokeLinecap="round" pathLength={100} strokeDasharray={`${Math.round(n.mastery * 100)} 100`} transform={`rotate(-90 ${n.x} ${n.y})`} opacity={n.mastery > 0 ? 0.9 : 0} />
              <text x={n.x} y={n.y + 10} textAnchor="middle" fontSize="3.1" fontWeight="800" fill="var(--ink)">{n.title}</text>
              <text x={n.x} y={n.y + 13.6} textAnchor="middle" fontSize="2.4" fill="var(--ink-2)">Class {n.grade}</text>
            </g>
          ))}
        </svg>
        <div className={s.legend}>{(['secure', 'learning', 'gap_confirmed', 'unassessed'] as Band[]).map((b) => <span key={b}><i style={{ background: FILL[b] }} />{LABEL[b]}</span>)}<span><i style={{ background: 'transparent', border: '2px dashed var(--brand)' }} />Ready to learn next</span></div>
      </Card>
      {sel && (
        <Card flat><div className={s.between}><div><h3>{sel.title}</h3><p className="muted sm">Class {sel.grade}{sel.inChapter ? '' : ' · from an earlier class'}</p></div><Chip tone={sel.band === 'secure' ? 'ok' : sel.band === 'gap_confirmed' ? 'gap' : sel.band === 'learning' ? 'hi' : 'soft'}>{LABEL[sel.band]}</Chip></div>
          <div className={s.row} style={{ marginTop: 12 }}>{sel.lessonId && <Button to={`/lesson/${sel.lessonId}`} variant="brand" size="sm" iconRight="arrowR">Open the lesson</Button>}<Button to={`/practice?concept=${sel.id}`} variant="ghost" size="sm" icon="target">Practise</Button></div></Card>
      )}
    </div>
  );
}
