import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../api/useApi';
import { api } from '../../api/client';
import type { Band, ClassOverview, ClassSummary } from '../../api/types';
import { Avatar, Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

const CELL: Record<Band, string> = { secure: s.cSecure, learning: s.cLearning, gap_confirmed: s.cGap, gap_suspected: s.cLearning, unassessed: s.cUn };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough evidence' };

export default function ClassView() {
  const params = useParams();
  const toast = useToast();
  const list = useApi<ClassSummary[]>('/teacher/classes');
  const id = params.id ?? list.data?.[0]?.id ?? null;
  const ov = useApi<ClassOverview>(id ? `/teacher/classes/${id}` : null);

  if (list.loading && !list.data) return <div className={s.stack}><Skeleton h={44} w="30%" /><Skeleton h={300} r={16} /></div>;
  if (list.data && list.data.length === 0) {
    return <Card><EmptyState icon="people" title="Create your first class" text="Students join with a class code. You will see who is secure, who is learning and who has a gap." action={<Button variant="brand" icon="plus" onClick={async () => { await api('/teacher/classes', { method: 'POST', body: { name: 'My class', grade: 7, subject: 'maths' } }); list.reload(); }}>Create class</Button>} /></Card>;
  }
  if (!ov.data) return ov.error ? <EmptyState icon="wifiOff" title="Could not load this class" text={ov.error.message} action={<Button onClick={ov.reload} icon="refresh">Try again</Button>} /> : <Skeleton h={420} r={16} />;
  const { cls, heatmap, recommendations, needsHelp } = ov.data;

  return (
    <div className={s.stack}>
      <div className={s.between}>
        <div><h1 className={s.title}>{cls.name}</h1><p className={s.lead}>{cls.students} students · concept understanding from real answers.</p></div>
        <div className={s.row}>
          <Chip icon="lock">Code {cls.joinCode}</Chip>
          <Button size="sm" variant="ghost" icon="share" onClick={() => { void navigator.clipboard?.writeText(cls.joinCode); toast('Class code copied', 'ok'); }}>Copy</Button>
          <Button to="/teacher/assign" size="sm" icon="clipboard">Assign work</Button>
        </div>
      </div>

      {recommendations.map((r) => (
        <Reveal key={r.id}><div className={s.reco}>
          <strong>Needs your attention</strong>
          <p className="sm">{r.text} <span className="muted">(evidence: {r.evidence})</span></p>
          <div className={s.row}>{r.lessonId && <Button to={`/teacher/assign?lesson=${r.lessonId}`} size="sm" variant="ghost" icon="clipboard">Assign “{r.lessonTitle}”</Button>}<Chip icon="people">{r.students} students</Chip></div>
        </div></Reveal>
      ))}

      {needsHelp.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Students who need help</h2>
          <div className={s.grid}>{needsHelp.map((n) => (
            <Card key={n.id} to={`/teacher/student/${n.id}`}><div className={s.row}><Avatar id={n.avatar} size={44} /><div><strong>{n.nickname}</strong><div className="sm muted">{n.reason}</div></div></div></Card>
          ))}</div>
        </section>
      )}

      <section>
        <h2 style={{ marginBottom: 12 }}>Concept heatmap</h2>
        <Card>
          <div style={{ overflowX: 'auto' }}>
            <div className={s.heat} style={{ ['--n' as string]: heatmap.concepts.length } as React.CSSProperties} role="table" aria-label="Students by concept">
              <span />{heatmap.concepts.map((c) => <span key={c.id} className={s.heatH}>{c.title}</span>)}
              {heatmap.students.map((st) => (
                <div key={st.id} style={{ display: 'contents' }} role="row">
                  <Link to={`/teacher/student/${st.id}`} className={s.row} style={{ gap: 8 }}><Avatar id={st.avatar} size={28} />{st.nickname}</Link>
                  {st.cells.map((b, i) => <i key={i} className={`${s.cell} ${CELL[b]}`} title={`${st.nickname}: ${heatmap.concepts[i].title}: ${NAME[b]}`} role="cell" aria-label={NAME[b]} />)}
                </div>
              ))}
            </div>
          </div>
          <div className={s.legend}><span><i style={{ background: 'var(--ok)' }} />Secure</span><span><i style={{ background: 'var(--hi)' }} />Learning</span><span><i style={{ background: 'var(--gap)' }} />Gap found</span><span><i style={{ borderStyle: 'dashed' }} />Not enough evidence</span></div>
        </Card>
      </section>
      <p className="sm muted"><Icon name="info" size={16} /> Suggestions are based on student answers. You decide what to assign.</p>
    </div>
  );
}
