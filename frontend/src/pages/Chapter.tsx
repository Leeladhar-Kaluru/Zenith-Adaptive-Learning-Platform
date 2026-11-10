import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import type { Band, BossStatus, ChapterDetail, Lesson } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { Icon } from '../icons/Icon';
import { savePack } from '../offline/db';
import { Button, Card, Chip, EmptyState, Progress, Reveal, Skeleton, useToast } from '../ui/kit';
import s from './pages.module.css';

const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { secure: 'ok', learning: 'hi', gap_confirmed: 'gap', gap_suspected: 'hi', unassessed: 'soft' };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not started' };

function Boss({ slug }: { slug: string }) {
  const { data } = useApi<BossStatus>(`/boss/${slug}`);
  if (!data) return null;
  const pct = Math.round(data.meanMastery * 100);
  return (
    <Card flat>
      <div className={s.between}><strong>Chapter boss quiz</strong><Chip tone={data.unlocked ? 'ok' : 'soft'} icon={data.unlocked ? 'check' : 'lock'}>{data.unlocked ? 'Open' : 'Locked'}</Chip></div>
      <p className="sm muted" style={{ marginTop: 6 }}>{data.unlocked ? 'Harder questions made for you across the whole chapter. Score 75 percent to beat it.' : data.reason}</p>
      <div style={{ marginTop: 10 }}><Progress value={Math.min(100, (pct / Math.round(data.needed * 100)) * 100)} label="Progress to unlock the boss quiz" /></div>
      <div className="sm muted" style={{ marginTop: 6 }}>Mastery in this chapter: {pct}% (opens at {Math.round(data.needed * 100)}%)</div>
      {data.unlocked && <div style={{ marginTop: 12 }}><Button to={`/tests/new?kind=boss&chapter=${slug}`} variant="brand" icon="trophy">Take the boss quiz</Button></div>}
    </Card>
  );
}

export default function Chapter() {
  const { slug = '' } = useParams();
  const toast = useToast();
  const { data, error, loading, reload } = useApi<ChapterDetail>(`/library/chapters/${slug}`);
  const [saving, setSaving] = useState(false);
  const { profile } = useAuth();

  if (loading && !data) return <div className={s.stack}><Skeleton h={44} w="50%" /><Skeleton h={90} /><Skeleton h={300} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not open this chapter" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const { chapter, lessons, prerequisites, concepts } = data;
  const gaps = prerequisites.filter((p) => p.band === 'gap_confirmed' || p.band === 'gap_suspected');
  const done = lessons.filter((l) => l.state === 'done').length;
  const cur = lessons.find((l) => l.state === 'current');

  async function save() {
    setSaving(true);
    try {
      const full = await Promise.all(lessons.map((l) => api<Lesson>(`/library/lessons/${l.id}`)));
      await savePack(chapter.slug, chapter.title, full);
      toast('Saved. You can read this chapter without internet.', 'ok');
    } catch (e) { toast((e as Error).message, 'err'); } finally { setSaving(false); }
  }

  if (chapter.status !== 'published') return <EmptyState icon="clock" title={`${chapter.title} is coming soon`} text="A teacher is still reviewing this chapter. It opens as soon as every lesson is approved." action={<Button to="/learn" variant="ghost">Back to Learn</Button>} />;

  return (
    <div data-subject={chapter.subject} className={s.stack}>
      <div>
        <Link to="/learn" className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />All chapters</Link>
        <h1 className={s.title} style={{ marginTop: 6 }}>{chapter.title}</h1>
        <p className={s.lead}>{data.summary}</p>
        <div className={s.row} style={{ marginTop: 14 }}>
          <Chip icon="book">{lessons.length} lessons</Chip><Chip icon="puzzle">{chapter.conceptCount} topics</Chip>
          <Button to={`/map/${chapter.slug}`} variant="ghost" size="sm" icon="layers">Concept map</Button>
          <Button variant="ghost" size="sm" icon="download" loading={saving} onClick={() => void save()}>Save for offline</Button>
        </div>
      </div>

      {gaps.map((g) => (
        <Reveal key={g.conceptId}><div className={s.prereq}><Icon name="compass" size={30} accent="var(--gap)" />
          <div style={{ flex: 1 }}><strong>Strengthen this first</strong><div className="sm">{g.title} (Class {g.grade}). Your answers suggest a gap here that can make this chapter harder.</div></div>
          {g.lessonId && <Button to={`/lesson/${g.lessonId}`} size="sm" variant="ghost">Open refresher</Button>}</div></Reveal>
      ))}

      <Card flat>
        <div className={s.between}><strong>Your progress</strong><span className="muted sm">{done} of {lessons.length} lessons done</span></div>
        <div style={{ marginTop: 10 }}><Progress value={(done / Math.max(1, lessons.length)) * 100} label="Chapter progress" /></div>
        <div className={s.row} style={{ marginTop: 16 }}>
          {cur && <Button to={`/lesson/${cur.id}`} iconRight="arrowR">{done === 0 ? 'Start chapter' : 'Continue'}: {cur.title}</Button>}
          <Button to={`/practice?chapter=${chapter.slug}`} variant="ghost" icon="target">Practise</Button>
          <Button to={`/tests/new?kind=diagnostic&chapter=${chapter.slug}`} variant="ghost" icon="search">Where am I?</Button>
          <Button to={`/tests/new?kind=chapter_test&chapter=${chapter.slug}`} variant="ghost" icon="clipboard">Chapter test</Button>
        </div>
      </Card>

      {profile?.role === 'student' && <Boss slug={chapter.slug} />}

      {data.objectives.length > 0 && <Card flat><h3>What you will learn</h3><ul style={{ margin: '8px 0 0 1.2em' }}>{data.objectives.map((o) => <li key={o}>{o}</li>)}</ul></Card>}

      <section><h2 style={{ marginBottom: 14 }}>Lessons</h2>
        <div className={s.lessons}>{lessons.map((l, i) => (
          <Reveal key={l.id} delay={i * 50}>
            <Link to={`/lesson/${l.id}`} className={`${s.lrow} ${l.state === 'done' ? s.done : ''}`} viewTransition>
              <span className={`${s.lnum} ${l.state === 'current' ? s.cur : ''}`}>{l.state === 'done' ? <Icon name="check" size={20} /> : l.order}</span>
              <div style={{ flex: 1 }}><strong>{l.title}</strong><div className="sm muted">{l.minutes} min</div></div>
              {l.state === 'current' && <Chip tone="hi">Up next</Chip>}<Icon name="chevR" size={20} />
            </Link>
          </Reveal>
        ))}</div>
      </section>

      {concepts.length > 0 && <section><h2 style={{ marginBottom: 14 }}>Topics in this chapter</h2>
        <div className={s.stack}>{concepts.map((c) => <div key={c.id} className={s.between}><div><strong>{c.title}</strong><div className="sm muted">{c.evidence} answer{c.evidence === 1 ? '' : 's'}</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>)}</div></section>}
    </div>
  );
}
