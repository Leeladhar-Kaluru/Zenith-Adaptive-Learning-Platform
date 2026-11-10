import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { useApi } from '../../api/useApi';
import type { Chapter, ClassSummary } from '../../api/types';
import { Button, Card, EmptyState, Segmented, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

export default function Assign() {
  const [q] = useSearchParams();
  const nav = useNavigate();
  const toast = useToast();
  const classes = useApi<ClassSummary[]>('/teacher/classes');
  const [classId, setClassId] = useState<string | null>(null);
  const cls = classes.data?.find((c) => c.id === classId) ?? classes.data?.[0];
  const chapters = useApi<Chapter[]>(cls ? `/library/chapters?grade=${cls.grade}&subject=${cls.subject}` : null);
  const [chapter, setChapter] = useState<string | null>(null);
  const [kind, setKind] = useState<'lesson' | 'practice' | 'reassess'>(q.get('lesson') ? 'lesson' : 'practice');
  const [due, setDue] = useState('');
  const [busy, setBusy] = useState(false);

  if (classes.loading && !classes.data) return <Skeleton h={300} r={16} />;
  if (!cls) return <EmptyState icon="people" title="Create a class first" text="Assignments go to a class." action={<Button to="/teacher" variant="brand">Go to classes</Button>} />;
  const published = (chapters.data ?? []).filter((c) => c.status === 'published');

  async function submit() {
    setBusy(true);
    try {
      await api('/teacher/assign', { method: 'POST', body: { classId: cls!.id, chapterSlug: chapter, lessonId: q.get('lesson'), kind, due: due || null } });
      toast('Assigned to your class', 'ok');
      nav('/teacher');
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.stack} style={{ maxWidth: 720 }}>
      <div><h1 className={s.title}>Assign work</h1><p className={s.lead}>Students see it on their Today screen. You choose; ZENITH never assigns on its own.</p></div>
      <Card>
        <div className={s.stack}>
          {classes.data && classes.data.length > 1 && <Segmented label="Class" value={cls.id} onChange={setClassId} options={classes.data.map((c) => ({ value: c.id, label: c.name }))} />}
          <div><span className="sm muted">What kind of work</span><div><Segmented label="Kind" value={kind} onChange={setKind} options={[{ value: 'lesson', label: 'Lesson' }, { value: 'practice', label: 'Practice set' }, { value: 'reassess', label: 'Reassessment' }]} /></div></div>
          <label className={s.field}>Chapter
            <select className={s.input} value={chapter ?? ''} onChange={(e) => setChapter(e.target.value || null)}>
              <option value="">Choose a chapter</option>
              {published.map((c) => <option key={c.id} value={c.slug}>Chapter {c.number}: {c.title}</option>)}
            </select>
          </label>
          <label className={s.field}>Due date (optional)<input className={s.input} type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
          <Button variant="brand" loading={busy} disabled={!chapter && !q.get('lesson')} onClick={submit} iconRight="send">Assign to {cls.name}</Button>
        </div>
      </Card>
    </div>
  );
}
