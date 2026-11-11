import { useState } from 'react';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import { useAuth } from '../context/AuthContext';
import type { ClassCard, Profile } from '../api/types';
import { Avatar, Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton, useToast } from '../ui/kit';
import s from './pages.module.css';
import c from './classes.module.css';

export const dueText = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : null);

export default function MyClasses() {
  const { data, error, loading, reload } = useApi<ClassCard[]>('/classes');
  const { setProfile } = useAuth();
  const toast = useToast();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  async function join() {
    setBusy(true);
    try {
      setProfile(await api<Profile>('/profile', { method: 'PUT', body: { classCode: code } }));
      setCode('');
      toast('Joined your class', 'ok');
      reload();
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.stack}>
      <div className={c.top}><h1 className={s.title}>My Classes</h1><p className={s.lead}>Your classrooms, teachers, announcements and work set for you.</p></div>
      {loading && !data && <Skeleton h={150} r={16} />}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load your classes" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && data.length === 0 && <Card><EmptyState icon="people" title="You have not joined a class yet" text="Ask your teacher for the class code (it looks like ZEN-XXXX) and enter it below." /></Card>}
      {data && data.length > 0 && (
        <div className={s.grid}>{data.map((k, i) => (
          <Reveal key={k.id} delay={Math.min(i, 8) * 40}>
            <Card to={`/classes/${k.id}`}>
              <h3 style={{ overflowWrap: 'anywhere' }}>{k.name}</h3>
              <div className={c.meta}><Chip tone="soft">Class {k.grade}</Chip><Chip tone="soft">{k.subject}</Chip><Chip tone="soft" icon="people">{k.classmates}</Chip></div>
              <div className={c.teacher}><Avatar id={k.teacher.avatar} size={30} /><span>{k.teacher.name}</span></div>
              {k.nextDue && <div className={c.next}><Icon name="clock" size={16} /> Next: <strong>{k.nextDue.title}</strong>{dueText(k.nextDue.dueAt) && <> · due {dueText(k.nextDue.dueAt)}</>}</div>}
            </Card>
          </Reveal>
        ))}</div>
      )}
      <Card flat>
        <h3>Join a class</h3>
        <p className="muted sm" style={{ margin: '6px 0 12px' }}>Enter the code your teacher gave you.</p>
        <div className={c.join}>
          <input className={s.input} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="ZEN-XXXX" maxLength={12} aria-label="Class code" />
          <Button variant="brand" disabled={code.length < 4} loading={busy} onClick={() => void join()}>Join</Button>
        </div>
      </Card>
    </div>
  );
}
