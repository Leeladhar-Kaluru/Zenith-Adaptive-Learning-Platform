import { Link, useParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import type { ChapterDetail } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Progress, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

export default function Chapter() {
  const { slug = '' } = useParams();
  const { data, error, loading, reload } = useApi<ChapterDetail>(`/library/chapters/${slug}`);
  if (loading && !data) return <div className={s.stack}><Skeleton h={44} w="50%" /><Skeleton h={90} /><Skeleton h={300} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not open this chapter" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const { chapter, lessons, prerequisites } = data;
  const gaps = prerequisites.filter((p) => p.band === 'gap_confirmed' || p.band === 'gap_suspected');
  const done = lessons.filter((l) => l.state === 'done').length;
  const cur = lessons.find((l) => l.state === 'current') ?? lessons.find((l) => l.state === 'todo');

  return (
    <div data-subject={chapter.subject} className={s.stack}>
      <div>
        <Link to="/learn" className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />All chapters</Link>
        <h1 className={s.title} style={{ marginTop: 6 }}>{chapter.title}</h1>
        <p className={s.lead}>{data.summary}</p>
        <div className={s.row} style={{ marginTop: 14 }}>
          <Chip icon="book">{lessons.length} lessons</Chip><Chip icon="puzzle">{chapter.conceptCount} concepts</Chip>
          <Button to={`/map/${chapter.slug}`} variant="ghost" size="sm" icon="layers">Concept map</Button>
        </div>
      </div>

      {gaps.map((g) => (
        <Reveal key={g.conceptId}><div className={s.prereq}>
          <Icon name="compass" size={30} accent="var(--gap)" />
          <div style={{ flex: 1 }}><strong>Strengthen this first</strong><div className="sm">{g.title} (Class {g.grade}). We found a gap here that can make this chapter harder.</div></div>
          {g.lessonId && <Button to={`/lesson/${g.lessonId}`} size="sm" variant="ghost">5-minute refresher</Button>}
        </div></Reveal>
      ))}

      <Card flat>
        <div className={s.between}><strong>Your progress</strong><span className="muted sm">{done} of {lessons.length} done</span></div>
        <div style={{ marginTop: 10 }}><Progress value={(done / Math.max(1, lessons.length)) * 100} label="Chapter progress" /></div>
        {cur && <div style={{ marginTop: 16 }}><Button to={`/lesson/${cur.id}`} iconRight="arrowR">{done === 0 ? 'Start chapter' : 'Continue'}: {cur.title}</Button></div>}
      </Card>

      <section>
        <h2 style={{ marginBottom: 14 }}>Lessons</h2>
        <div className={s.lessons}>
          {lessons.map((l, i) => (
            <Reveal key={l.id} delay={i * 50}>
              <Link to={`/lesson/${l.id}`} className={`${s.lrow} ${l.state === 'done' ? s.done : ''}`} viewTransition>
                <span className={`${s.lnum} ${l.state === 'current' ? s.cur : ''}`}>{l.state === 'done' ? <Icon name="check" size={20} /> : l.order}</span>
                <div style={{ flex: 1 }}><strong>{l.title}</strong><div className="sm muted">{l.minutes} min</div></div>
                {l.state === 'current' && <Chip tone="hi">Up next</Chip>}
                <Icon name="chevR" size={20} />
              </Link>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
