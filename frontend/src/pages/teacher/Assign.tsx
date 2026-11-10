import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { clearApiCache, useApi } from '../../api/useApi';
import type { CatalogChapter, ClassSummary } from '../../api/types';
import { Button, Card, EmptyState, Segmented, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

export default function Assign() {
  const [q] = useSearchParams();
  const nav = useNavigate();
  const toast = useToast();
  const classes = useApi<ClassSummary[]>('/teacher/classes');
  const [classId, setClassId] = useState<string | null>(q.get('class'));
  const cls = classes.data?.find((c) => c.id === classId) ?? classes.data?.[0];
  const catalog = useApi<CatalogChapter[]>(cls ? `/teacher/catalog?grade=${cls.grade}&subject=${cls.subject}` : null);
  const preLesson = q.get('lesson');
  const [kind, setKind] = useState<'lesson' | 'practice' | 'test'>(preLesson ? 'lesson' : 'practice');
  const [chapter, setChapter] = useState<string>('');
  const [lesson, setLesson] = useState<string>(preLesson ?? '');
  const [due, setDue] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  if (classes.loading && !classes.data) return <Skeleton h={300} r={16} />;
  if (!cls) return <EmptyState icon="people" title="Create a class first" text="Assignments go to a class." action={<Button to="/teacher" variant="brand">Go to classes</Button>} />;
  const chap = catalog.data?.find((c) => c.slug === chapter);
  const ready = kind === 'lesson' ? !!lesson : !!chapter || !!q.get('concept');

  async function submit() {
    setBusy(true);
    try {
      await api('/teacher/assignments', { method: 'POST', body: {
        classId: cls!.id, kind, chapter: kind === 'lesson' ? undefined : chapter || undefined, lessonId: kind === 'lesson' ? lesson : undefined,
        conceptIds: q.get('concept') ? [q.get('concept')] : [], due: due ? new Date(due).toISOString() : undefined, note: note || undefined,
        suggestionKey: q.get('key') || undefined, studentIds: (q.get('students') ?? '').split(',').filter(Boolean),
      } });
      clearApiCache();
      toast('Assigned to your class', 'ok');
      nav(`/teacher/class/${cls!.id}`);
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.stack} style={{ maxWidth: 720 }}>
      <div><h1 className={s.title}>Assign work</h1><p className={s.lead}>Students see it on Home. You choose; ZENITH never assigns on its own.</p></div>
      <Card><div className={s.stack}>
        {classes.data && classes.data.length > 1 && <Segmented label="Class" value={cls.id} onChange={setClassId} options={classes.data.map((c) => ({ value: c.id, label: c.name }))} />}
        <div><span className="sm muted">What kind of work</span><div><Segmented label="Kind" value={kind} onChange={setKind} options={[{ value: 'lesson', label: 'Lesson' }, { value: 'practice', label: 'Practice' }, { value: 'test', label: 'Test' }]} /></div></div>
        {catalog.data && catalog.data.length === 0 && <p className="muted sm">No chapters are published for this class yet. Approve content in Review first.</p>}
        <label className={s.field}>Chapter
          <select className={s.input} value={chapter} onChange={(e) => { setChapter(e.target.value); setLesson(''); }}>
            <option value="">Choose a chapter</option>{catalog.data?.map((c) => <option key={c.slug} value={c.slug}>{c.title}</option>)}
          </select></label>
        {kind === 'lesson' && (
          <label className={s.field}>Lesson
            <select className={s.input} value={lesson} onChange={(e) => setLesson(e.target.value)}>
              <option value="">Choose a lesson</option>
              {(chap ? [chap] : catalog.data ?? []).flatMap((c) => c.lessons.map((l) => <option key={l.id} value={l.id}>{c.title}: {l.title}</option>))}
            </select></label>
        )}
        <label className={s.field}>Due date (optional)<input className={s.input} type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
        <label className={s.field}>Note to students (optional)<input className={s.input} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} /></label>
        <Button variant="brand" loading={busy} disabled={!ready} onClick={() => void submit()} iconRight="send">Assign to {cls.name}</Button>
      </div></Card>
    </div>
  );
}
