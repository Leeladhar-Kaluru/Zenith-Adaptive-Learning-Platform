import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/useApi';
import type { Boards, Chapter, SearchResults, Subject } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Progress, Reveal, Segmented, Skeleton } from '../ui/kit';
import { Coverage } from './Coverage';
import s from './pages.module.css';

export function ChapterCard({ c, delay = 0 }: { c: Chapter; delay?: number }) {
  const soon = c.status === 'coming_soon';
  const pct = c.progress ? (c.progress.done / Math.max(1, c.progress.total)) * 100 : 0;
  return (
    <Reveal delay={delay}>
      <div data-subject={c.subject}>
        <Card to={soon ? undefined : `/learn/${c.slug}`} dashed={soon} className={s.chap}>
          <div className={s.chapArt}><Icon name={c.subject === 'maths' ? 'ruler' : c.subject === 'social' ? 'globe' : ['english', 'hindi', 'telugu'].includes(c.subject) ? 'book' : 'flask'} size={52} accent="var(--subject)" /></div>
          <div className={s.chapBody}>
            <div className={s.between}>
              <span className={s.num}>Chapter {c.number}</span>
              <Chip tone={soon ? 'soft' : 'ok'}>{soon ? 'Coming soon' : 'Ready'}</Chip>
            </div>
            <h3>{c.title}</h3>
            {soon ? <p className="muted sm">Being reviewed by a teacher before it opens.</p> : (<>
              <p className="muted sm">{c.lessonCount} lessons · {c.conceptCount} concepts</p>
              <Progress value={pct} label={`${c.title} progress`} />
              <span className="sm muted">{c.progress && c.progress.done > 0 ? `${c.progress.done} of ${c.progress.total} done` : 'Not started'}</span>
            </>)}
          </div>
        </Card>
      </div>
    </Reveal>
  );
}

export default function Learn() {
  const { profile } = useAuth();
  const [grade, setGrade] = useState<number>(profile?.grade ?? 7);
  const boards = useApi<Boards>('/library/boards');
  const [subject, setSubject] = useState<Subject>('maths');
  const [q, setQ] = useState('');
  const search = useApi<SearchResults>(q.trim().length >= 2 ? `/library/search?q=${encodeURIComponent(q.trim())}` : null);
  const { data, error, loading, reload } = useApi<Chapter[]>(`/library/chapters?grade=${grade}&subject=${subject}`);

  return (
    <div data-subject={subject}>
      <h1 className={s.title}>Learn</h1>
      <p className={s.lead}>Pick your class. A chapter opens once a teacher has reviewed it.</p>
      <div className={s.filters}>
        <Segmented label="Class" value={grade} onChange={setGrade} options={[6, 7, 8, 9, 10].map((g) => ({ value: g, label: String(g) }))} />
        <Segmented label="Subject" value={subject} onChange={setSubject} options={(boards.data?.subjects ?? []).map((x) => ({ value: x.id, label: x.name }))} />
        <input className={s.input} style={{ maxWidth: 280 }} type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search chapters and topics" aria-label="Search chapters and topics" />
      </div>
      {q.trim().length >= 2 && search.data && (
        <Card flat style={{ marginBottom: 22 }}><h3>Search results</h3>
          {search.data.chapters.length + search.data.lessons.length + search.data.concepts.length === 0 && <p className="muted">Nothing matched in your class. Try a different word.</p>}
          <div className={s.stack} style={{ marginTop: 10 }}>
            {search.data.chapters.map((c) => <Link key={c.id} to={`/learn/${c.slug}`} className={s.lrow}><div style={{ flex: 1 }}><strong>{c.title}</strong><div className="sm muted">Chapter · Class {c.grade}{c.status !== 'published' ? ' · coming soon' : ''}</div></div></Link>)}
            {search.data.lessons.map((l) => <Link key={l.id} to={`/lesson/${l.id}`} className={s.lrow}><div style={{ flex: 1 }}><strong>{l.title}</strong><div className="sm muted">Lesson · {l.chapter}</div></div></Link>)}
            {search.data.concepts.filter((c) => c.lessonId).map((c) => <Link key={c.id} to={`/lesson/${c.lessonId}`} className={s.lrow}><div style={{ flex: 1 }}><strong>{c.title}</strong><div className="sm muted">Topic · Class {c.grade}</div></div></Link>)}
          </div></Card>
      )}
      {profile?.role === 'student' && boards.data && <div style={{ marginBottom: 14 }}><Coverage subject={subject} grade={grade} name={boards.data.subjects.find((x) => x.id === subject)?.name ?? subject} /></div>}
      {loading && !data && <div className={s.grid}>{[0, 1, 2].map((i) => <Skeleton key={i} h={250} r={16} />)}</div>}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load chapters" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && data.length === 0 && <EmptyState icon="book" title="Nothing here yet" text={`No published ${boards.data?.subjects.find((x) => x.id === subject)?.name ?? subject} chapters for Class ${grade} yet. Use "Ask for more lessons" above and a teacher will be asked to review new ones.`} />}
      {data && data.length > 0 && <div className={s.grid}>{data.map((c, i) => <ChapterCard key={c.id} c={c} delay={i * 70} />)}</div>}
    </div>
  );
}
