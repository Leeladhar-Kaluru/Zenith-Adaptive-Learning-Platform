import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../api/useApi';
import type { Band, StudentDetail } from '../../api/types';
import { Avatar, Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Skeleton } from '../../ui/kit';
import s from '../pages.module.css';

const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { secure: 'ok', learning: 'hi', gap_confirmed: 'gap', gap_suspected: 'hi', unassessed: 'soft' };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough evidence' };

export default function StudentView() {
  const { id = '' } = useParams();
  const { data, error, loading, reload } = useApi<StudentDetail>(`/teacher/students/${id}`);
  if (loading && !data) return <div className={s.stack}><Skeleton h={60} w="40%" /><Skeleton h={260} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load this student" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  return (
    <div className={s.stack}>
      <Link to="/teacher" className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />Back to class</Link>
      <div className={s.row}><Avatar id={data.avatar} size={64} /><div><h1 className={s.title} style={{ fontSize: '2rem' }}>{data.nickname}</h1><p className="muted">Class {data.grade}</p></div></div>
      <div className={s.cols}>
        <Card><h3>Concepts</h3>
          <div className={s.stack} style={{ marginTop: 12 }}>{data.concepts.map((c) => <div key={c.id} className={s.between}><div><strong>{c.title}</strong><div className="sm muted">{c.evidenceCount} answers</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>)}</div>
        </Card>
        <Card><h3>Interventions</h3>
          {data.interventions.length === 0 ? <p className="muted sm" style={{ marginTop: 10 }}>No interventions yet.</p> : (
            <div className={s.stack} style={{ marginTop: 12 }}>{data.interventions.map((i, k) => (
              <div key={k} className={s.reco}><strong>{i.concept}</strong><div className={s.row}><Chip tone={TONE[i.before]}>{NAME[i.before]}</Chip><Icon name="arrowR" size={18} /><Chip tone={i.after ? TONE[i.after] : 'soft'}>{i.after ? NAME[i.after] : 'Reassessment pending'}</Chip></div></div>
            ))}</div>
          )}
          <div style={{ marginTop: 16 }}><Button to="/teacher/assign" size="sm" icon="clipboard">Assign a refresher</Button></div>
        </Card>
      </div>
      <Card><h3>Recent activity</h3>
        <ol style={{ listStyle: 'none', marginTop: 12, borderLeft: '3px solid var(--line)' }}>
          {data.timeline.map((t, i) => <li key={i} style={{ padding: '8px 0 8px 16px', position: 'relative' }}><span className="sm muted">{t.at}</span><div style={{ fontWeight: 700 }}>{t.text}</div></li>)}
        </ol>
      </Card>
    </div>
  );
}
