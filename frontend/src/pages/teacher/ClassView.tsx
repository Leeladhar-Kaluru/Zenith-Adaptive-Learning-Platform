import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { clearApiCache, useApi } from '../../api/useApi';
import type { Band, Boards, ClassOverview, ClassSummary } from '../../api/types';
import { Avatar, Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Segmented, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

const CELL: Record<Band, string> = { secure: s.cSecure, learning: s.cLearning, gap_confirmed: s.cGap, gap_suspected: s.cLearning, unassessed: s.cUn };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough evidence' };

function CreateClass({ onDone }: { onDone: () => void }) {
  const boards = useApi<Boards>('/library/boards');
  const toast = useToast();
  const [name, setName] = useState('');
  const [grade, setGrade] = useState(7);
  const [subject, setSubject] = useState('');
  const [busy, setBusy] = useState(false);
  const sub = subject || boards.data?.subjects[0]?.id || '';
  async function make() {
    setBusy(true);
    try { await api('/teacher/classes', { method: 'POST', body: { name: name.trim() || `Class ${grade}`, grade, subject: sub } }); clearApiCache(); onDone(); }
    catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }
  return (
    <Card style={{ maxWidth: 560 }}><h2>Create a class</h2><p className="muted sm" style={{ margin: '6px 0 14px' }}>Students join with a code. You will see who is secure, who is learning and who has a gap, from their real answers.</p>
      <div className={s.stack}>
        <label className={s.field}>Class name<input className={s.input} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. 7B Maths" maxLength={80} /></label>
        <div><span className="sm muted">Class</span><div><Segmented label="Class" value={grade} onChange={setGrade} options={[6, 7, 8, 9, 10].map((g) => ({ value: g, label: String(g) }))} /></div></div>
        <div><span className="sm muted">Subject</span><div><Segmented label="Subject" value={sub} onChange={setSubject} options={(boards.data?.subjects ?? []).map((x) => ({ value: x.id, label: x.name }))} /></div></div>
        <Button variant="brand" loading={busy} disabled={!sub} onClick={() => void make()} icon="plus">Create class</Button>
      </div></Card>
  );
}

export default function ClassView() {
  const params = useParams();
  const toast = useToast();
  const list = useApi<ClassSummary[]>('/teacher/classes');
  const [creating, setCreating] = useState(false);
  const id = params.id ?? list.data?.[0]?.id ?? null;
  const ov = useApi<ClassOverview>(id ? `/teacher/classes/${id}` : null);

  if (list.loading && !list.data) return <div className={s.stack}><Skeleton h={44} w="30%" /><Skeleton h={300} r={16} /></div>;
  if (list.error && !list.data) return <EmptyState icon="wifiOff" title="Could not load your classes" text={list.error.message} action={<Button onClick={list.reload} icon="refresh">Try again</Button>} />;
  if (!list.data || list.data.length === 0 || creating) return <div className={s.stack}><h1 className={s.title}>Classes</h1><CreateClass onDone={() => { setCreating(false); list.reload(); }} /></div>;
  if (!ov.data) return ov.error ? <EmptyState icon="wifiOff" title="Could not load this class" text={ov.error.message} action={<Button onClick={ov.reload} icon="refresh">Try again</Button>} /> : <Skeleton h={420} r={16} />;
  const { cls, concepts, heatmap, suggestions, needsHelp, assignments, trend } = ov.data;
  const classes = list.data;

  async function decide(key: string, action: 'dismissed') {
    try { await api(`/teacher/classes/${cls.id}/decisions`, { method: 'POST', body: { key, action } }); ov.reload(); } catch (e) { toast((e as Error).message, 'err'); }
  }
  async function leagues(enabled: boolean) {
    try { await api(`/teacher/classes/${cls.id}/leagues`, { method: 'PUT', body: { enabled } }); ov.reload(); toast(enabled ? 'Class league is on' : 'Class league is off', 'ok'); } catch (e) { toast((e as Error).message, 'err'); }
  }

  return (
    <div className={s.stack}>
      <div className={s.between}>
        <div><h1 className={s.title}>{cls.name}</h1><p className={s.lead}>{cls.students} student{cls.students === 1 ? '' : 's'} · understanding from their real answers.</p></div>
        <div className={s.row}>
          <Chip icon="lock">Code {cls.joinCode}</Chip>
          <Button size="sm" variant="ghost" icon="share" onClick={() => { void navigator.clipboard?.writeText(cls.joinCode); toast('Class code copied', 'ok'); }}>Copy</Button>
          <Button to={`/teacher/assign?class=${cls.id}`} size="sm" icon="clipboard">Assign work</Button>
        </div>
      </div>
      {classes.length > 1 && <Segmented label="Class" value={cls.id} onChange={(v) => { window.location.assign(`/teacher/class/${v}`); }} options={classes.map((c) => ({ value: c.id, label: c.name }))} />}

      {cls.students === 0 && <Card><EmptyState icon="people" title="No students yet" text={`Share the code ${cls.joinCode}. Students enter it in onboarding or Settings.`} /></Card>}

      {suggestions.map((r) => (
        <Reveal key={r.key}><div className={s.reco}>
          <strong>Needs your attention</strong>
          <p className="sm">{r.text} <span className="muted">(evidence: {r.evidence})</span></p>
          <div className={s.row}>
            {r.lessonId && <Button to={`/teacher/assign?class=${cls.id}&lesson=${r.lessonId}&concept=${r.conceptId}&key=${encodeURIComponent(r.key)}&students=${r.studentIds.join(',')}`} size="sm" variant="ghost" icon="clipboard">Assign “{r.lessonTitle}”</Button>}
            <Button size="sm" variant="ghost" icon="close" onClick={() => void decide(r.key, 'dismissed')}>Not needed</Button>
            <Chip icon="people">{r.students} students</Chip>
          </div>
        </div></Reveal>
      ))}

      {needsHelp.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Students who may need help</h2>
          <div className={s.grid}>{needsHelp.map((n) => (
            <Card key={n.id} to={`/teacher/class/${cls.id}/student/${n.id}`}><div className={s.row}><Avatar id={n.avatar} size={44} /><div><strong>{n.nickname}</strong><div className="sm muted">{n.reason}</div></div></div></Card>
          ))}</div>
        </section>
      )}

      {concepts.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Topic heatmap</h2>
          <Card><div style={{ overflowX: 'auto' }}>
            <div className={s.heat} style={{ ['--n' as string]: concepts.length } as React.CSSProperties} role="table" aria-label="Students by topic">
              <span />{concepts.map((c) => <span key={c.id} className={s.heatH}>{c.title}</span>)}
              {heatmap.map((st) => (
                <div key={st.id} style={{ display: 'contents' }} role="row">
                  <Link to={`/teacher/class/${cls.id}/student/${st.id}`} className={s.row} style={{ gap: 8 }}><Avatar id={st.avatar} size={28} />{st.nickname}</Link>
                  {st.cells.map((c, i) => <i key={i} className={`${s.cell} ${CELL[c.band]}`} title={`${st.nickname}: ${concepts[i].title}: ${NAME[c.band]} (${c.evidence} answers)`} role="cell" aria-label={`${NAME[c.band]}, ${c.evidence} answers`} />)}
                </div>
              ))}
            </div></div>
            <div className={s.legend}><span><i style={{ background: 'var(--ok)' }} />Secure</span><span><i style={{ background: 'var(--hi)' }} />Learning</span><span><i style={{ background: 'var(--gap)' }} />Gap found</span><span><i style={{ borderStyle: 'dashed' }} />Not enough evidence</span></div></Card>
        </section>
      )}

      {trend.length > 0 && <section><h2 style={{ marginBottom: 12 }}>Class activity, last 4 weeks</h2><Card>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 110 }} role="img" aria-label="Answers per day, with accuracy on hover">
          {trend.map((t) => <div key={t.day} title={`${t.day}: ${t.answers} answers, ${Math.round(t.accuracy * 100)}% right`} style={{ flex: 1, minWidth: 6, height: `${Math.max(8, Math.min(100, t.answers))}%`, background: t.accuracy >= 0.7 ? 'var(--ok)' : t.accuracy >= 0.5 ? 'var(--hi)' : 'var(--gap)', border: '2px solid var(--ink)', borderRadius: 6 }} />)}
        </div><p className="sm muted" style={{ marginTop: 8 }}>Bar height is answers that day. Colour is how many were right.</p></Card></section>}

      {assignments.length > 0 && <section><h2 style={{ marginBottom: 12 }}>Assignments</h2><div className={s.stack}>{assignments.map((a) => (
        <Card key={a.id} flat><div className={s.between}><div><strong>{a.title}</strong><div className="sm muted">{a.due ? `Due ${new Date(a.due).toLocaleDateString()}` : 'No due date'}</div></div><Chip tone={a.done === a.students && a.students > 0 ? 'ok' : 'soft'}>{a.done} of {a.students} done</Chip></div></Card>
      ))}</div></section>}

      <Card flat><div className={s.between}><div><strong>Class league</strong><p className="sm muted">Weekly, ranked by XP, nickname and character only. Students can hide themselves.</p></div>
        <Button size="sm" variant="ghost" onClick={() => void leagues(!cls.leaguesEnabled)}>{cls.leaguesEnabled ? 'Turn off' : 'Turn on'}</Button></div></Card>
      <div className={s.row}><Button size="sm" variant="ghost" icon="plus" onClick={() => setCreating(true)}>New class</Button><span className="sm muted"><Icon name="info" size={16} /> Suggestions come from student answers. You decide what to assign.</span></div>
    </div>
  );
}
