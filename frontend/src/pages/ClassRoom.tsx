import { lazy, Suspense, useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import type { ClassDetail } from '../api/types';
import { Avatar, Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Segmented, Skeleton, useToast } from '../ui/kit';
import { dueText } from './MyClasses';
import s from './pages.module.css';
import c from './classes.module.css';

type Tab = 'chat' | 'news' | 'work' | 'people' | 'reports';
const Chat = lazy(() => import('../chat/Chat').then((m) => ({ default: m.Chat })));
const Reports = lazy(() => import('../chat/Chat').then((m) => ({ default: m.Reports })));

/** Classmates you chose not to see in chat, with a way back. */
function Blocked() {
  const [rows, setRows] = useState<Array<{ id: string; nickname: string }>>([]);
  const load = useCallback(() => { api<Array<{ id: string; nickname: string }>>('/chat/blocks').then(setRows).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);
  if (rows.length === 0) return null;
  return (
    <Card flat style={{ marginTop: 12 }}>
      <strong>Hidden in chat</strong>
      {rows.map((r) => <div key={r.id} className={c.noteHead} style={{ marginTop: 8 }}><span>{r.nickname}</span><Button size="sm" variant="ghost" onClick={() => void api(`/chat/blocks/${r.id}`, { method: 'DELETE' }).then(load)}>Show again</Button></div>)}
    </Card>
  );
}

export default function ClassRoom() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data, error, loading, reload } = useApi<ClassDetail>(`/classes/${id}`);
  const [tab, setTab] = useState<Tab>('chat');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [pinned, setPinned] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try { await fn(); toast(ok, 'ok'); reload(); } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }
  const post = () => run(async () => {
    await api(`/classes/${id}/announcements`, { method: 'POST', body: { title, body, pinned } });
    setTitle(''); setBody(''); setPinned(false);
  }, 'Announcement posted');
  const leave = async () => {
    setBusy(true);
    try { await api(`/classes/${id}/membership`, { method: 'DELETE' }); toast('You left the class', 'ok'); nav('/classes', { replace: true }); }
    catch (e) { toast((e as Error).message, 'err'); setBusy(false); }
  };

  if (loading && !data) return <Skeleton h={220} r={16} />;
  if (error && !data) {
    return <EmptyState icon="people" title="Class not found" text="This class does not exist, or you are not a member of it." action={<Button to="/classes" icon="arrowL">My Classes</Button>} />;
  }
  if (!data) return null;

  return (
    <div className={s.stack}>
      <div className={c.top}>
        <Button to={data.isTeacher ? '/teacher' : '/classes'} variant="ghost" size="sm" icon="arrowL">{data.isTeacher ? 'Teacher workspace' : 'My Classes'}</Button>
        <h1 className={s.title} style={{ overflowWrap: 'anywhere' }}>{data.name}</h1>
        <div className={c.meta}><Chip tone="soft">Class {data.grade}</Chip><Chip tone="soft">{data.subject}</Chip></div>
        <div className={c.teacher}><Avatar id={data.teacher.avatar} size={32} /><span>Taught by {data.teacher.name}</span></div>
      </div>

      <div className={c.tabs}>
        <Segmented<Tab> label="Class sections" value={tab} onChange={setTab}
          options={[{ value: 'chat', label: 'Chat' }, { value: 'news', label: `News (${data.announcements.length})` }, { value: 'work', label: `Work (${data.assignments.length})` }, { value: 'people', label: `People (${data.classmates.length})` }, ...(data.isTeacher ? [{ value: 'reports' as Tab, label: data.openReports ? `Reports (${data.openReports})` : 'Reports' }] : [])]} />
      </div>

      {tab === 'chat' && <Suspense fallback={<Skeleton h={320} r={16} />}><Chat classId={id} isTeacher={data.isTeacher} /></Suspense>}
      {tab === 'reports' && data.isTeacher && <Suspense fallback={<Skeleton h={80} r={16} />}><Reports classId={id} /></Suspense>}

      {tab === 'news' && (
        <section className={c.list} aria-label="Announcements">
          {data.isTeacher && (
            <Card flat>
              <div className={c.compose}>
                <h3>New announcement</h3>
                <label className={s.field}>Title<input className={s.input} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} /></label>
                <label className={s.field}>Message<textarea className={s.input} value={body} onChange={(e) => setBody(e.target.value)} maxLength={4000} /></label>
                <label className={c.check}><input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} /> Pin to the top</label>
                <div className={c.actions}><Button variant="brand" icon="check" loading={busy} disabled={!title.trim() || !body.trim()} onClick={() => void post()}>Post</Button></div>
              </div>
            </Card>
          )}
          {data.announcements.length === 0
            ? <Card><EmptyState icon="bell" title="No announcements yet" text={data.isTeacher ? 'Post the first one above.' : 'Your teacher has not posted anything yet.'} /></Card>
            : data.announcements.map((a) => (
              <Card key={a.id} flat className={c.note}>
                <div className={c.noteHead}>
                  <div><h3>{a.title}</h3><div className={c.noteMeta}>{a.author} · {new Date(a.createdAt).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}</div></div>
                  {a.pinned && <Chip tone="hi" icon="flag">Pinned</Chip>}
                </div>
                <p>{a.body}</p>
                {data.isTeacher && (
                  <div className={c.actions} style={{ marginTop: 12 }}>
                    <Button size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => api(`/classes/${id}/announcements/${a.id}/pin`, { method: 'PUT', body: { pinned: !a.pinned } }), a.pinned ? 'Unpinned' : 'Pinned')}>{a.pinned ? 'Unpin' : 'Pin'}</Button>
                    <Button size="sm" variant="danger" icon="trash" disabled={busy} onClick={() => void run(() => api(`/classes/${id}/announcements/${a.id}`, { method: 'DELETE' }), 'Deleted')}>Delete</Button>
                  </div>
                )}
              </Card>
            ))}
        </section>
      )}

      {tab === 'work' && (
        <section className={c.list} aria-label="Work set for this class">
          {data.assignments.length === 0
            ? <Card><EmptyState icon="clipboard" title="Nothing set yet" text="Work your teacher sets for this class will show up here with its due date." /></Card>
            : data.assignments.map((a) => (
              <Card key={a.id} flat to={a.href ?? undefined}>
                <div className={c.noteHead}><h3 style={{ overflowWrap: 'anywhere' }}>{a.title}</h3><Chip tone="soft">{a.kind}</Chip></div>
                {a.note && <p className="muted sm" style={{ marginTop: 6 }}>{a.note}</p>}
                <div className={c.noteMeta}><Icon name="clock" size={14} /> {dueText(a.dueAt) ? `Due ${dueText(a.dueAt)}` : 'No due date'}</div>
              </Card>
            ))}
        </section>
      )}

      {tab === 'people' && (
        <section aria-label="Classmates">
          <div className={c.mates}>{data.classmates.map((m, i) => (
            <div key={`${m.nickname}-${i}`} className={c.mate}><Avatar id={m.avatar} size={34} /><span>{m.nickname}{m.me ? ' (you)' : ''}</span></div>
          ))}</div>
          {!data.isTeacher && <Blocked />}
          <p className={c.privacy} style={{ marginTop: 12 }}>Only nicknames and characters are shown. Classmates who prefer privacy appear as "A classmate".</p>
        </section>
      )}

      {!data.isTeacher && (
        <Card flat dashed>
          {confirmLeave ? (
            <div className={c.compose}>
              <strong>Leave {data.name}?</strong>
              <p className="muted sm">You will stop seeing its announcements and work. Your own progress stays safe, and you can rejoin with the class code.</p>
              <div className={c.actions}><Button variant="danger" loading={busy} onClick={() => void leave()}>Yes, leave</Button><Button variant="ghost" onClick={() => setConfirmLeave(false)}>Stay</Button></div>
            </div>
          ) : <Button variant="ghost" size="sm" onClick={() => setConfirmLeave(true)}>Leave this class</Button>}
        </Card>
      )}
    </div>
  );
}
