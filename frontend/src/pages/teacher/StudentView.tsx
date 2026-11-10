import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../api/useApi';
import type { Band, StudentDetail } from '../../api/types';
import { Avatar, Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Skeleton } from '../../ui/kit';
import s from '../pages.module.css';

const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { secure: 'ok', learning: 'hi', gap_confirmed: 'gap', gap_suspected: 'hi', unassessed: 'soft' };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough evidence' };

export default function StudentView() {
  const { cid = '', id = '' } = useParams();
  const { data, error, loading, reload } = useApi<StudentDetail>(`/teacher/classes/${cid}/students/${id}`);
  if (loading && !data) return <div className={s.stack}><Skeleton h={60} w="40%" /><Skeleton h={260} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load this student" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  return (
    <div className={s.stack}>
      <Link to={`/teacher/class/${cid}`} className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />Back to class</Link>
      <div className={s.row}><Avatar id={data.avatar} size={64} /><div><h1 className={s.title} style={{ fontSize: '2rem' }}>{data.name}</h1><p className="muted">Nickname {data.nickname} · Class {data.grade}</p></div></div>
      <div className={s.cols}>
        <Card><h3>Topics</h3>
          {data.concepts.length === 0 ? <p className="muted sm" style={{ marginTop: 10 }}>No answers yet.</p> : (
            <div className={s.stack} style={{ marginTop: 12 }}>{data.concepts.map((c) => <div key={c.id} className={s.between}><div><strong>{c.title}</strong><div className="sm muted">{c.correct} of {c.evidence} right · confidence {c.confidence}</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>)}</div>
          )}
        </Card>
        <Card><h3>Interventions</h3>
          {data.interventions.length === 0 ? <p className="muted sm" style={{ marginTop: 10 }}>None yet. Assigning work from a class suggestion records the starting point here.</p> : (
            <div className={s.stack} style={{ marginTop: 12 }}>{data.interventions.map((i, k) => (
              <div key={k} className={s.reco}><strong>{i.concept}</strong><div className={s.row}><Chip tone="soft">Before: {Math.round(i.before * 100)}%</Chip><Icon name="arrowR" size={18} /><Chip tone={i.after !== null ? 'ok' : 'soft'}>{i.after !== null ? `After: ${Math.round(i.after * 100)}%` : 'Still open'}</Chip></div></div>
            ))}</div>
          )}
          <div style={{ marginTop: 16 }}><Button to={`/teacher/assign?class=${cid}`} size="sm" icon="clipboard">Assign a refresher</Button></div>
        </Card>
      </div>
      <div className={s.cols}>
        <Card><h3>Difficulty level by topic</h3>
          {data.levels.length === 0 ? <p className="muted sm" style={{ marginTop: 10 }}>No adaptive practice yet.</p> : (
            <div className={s.stack} style={{ marginTop: 12 }}>{data.levels.map((l) => <div key={l.concept}><div className={s.between}><strong>{l.title}</strong><Chip tone="soft">Level {l.level} of 5</Chip></div>{l.reason && <div className="sm muted">{l.reason}</div>}</div>)}</div>
          )}
        </Card>
        <Card><h3>What they did in the last {data.activity.days} days</h3>
          <div className={s.stack} style={{ marginTop: 12 }}>
            <div className={s.between}><span>Reading time</span><strong>{data.activity.readingMinutes} min</strong></div>
            <div className={s.between}><span>Lessons opened</span><strong>{data.activity.lessonsOpened}</strong></div>
            <div className={s.between}><span>Hints opened</span><strong>{data.activity.hintsOpened}</strong></div>
            <div className={s.between}><span>Answers changed</span><strong>{data.activity.answerChanges}</strong></div>
            <div className={s.between}><span>Simulation moves</span><strong>{data.activity.simulationMoves}</strong></div>
          </div>
        </Card>
      </div>
      {data.mistakes.length > 0 && <Card><h3>Repeated mistakes</h3><div className={s.stack} style={{ marginTop: 12 }}>{data.mistakes.map((m) => <div key={m.itemId}><strong>{m.stem}</strong>{m.misconception && <div className="sm">Common mistake: {m.misconception}</div>}<div className="sm muted">Missed {m.missedTimes} time{m.missedTimes === 1 ? '' : 's'}</div></div>)}</div></Card>}
      <Card><h3>Recent activity</h3>
        {data.timeline.length === 0 ? <p className="muted sm" style={{ marginTop: 10 }}>No activity yet.</p> : (
          <ol style={{ listStyle: 'none', marginTop: 12, borderLeft: '3px solid var(--line)' }}>{data.timeline.map((t, i) => <li key={i} style={{ padding: '8px 0 8px 16px' }}><span className="sm muted">{new Date(t.at).toLocaleString()} · {t.context.replace('_', ' ')}</span><div style={{ fontWeight: 700 }}>{t.text}</div></li>)}</ol>
        )}
      </Card>
    </div>
  );
}
