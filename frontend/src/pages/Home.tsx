import { Link } from 'react-router-dom';
import { useApi } from '../api/useApi';
import type { Today } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, CountUp, EmptyState, Progress, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const KIND_ICON: Record<string, string> = { prereq: 'compass', lesson: 'book', practice: 'target', challenge: 'bolt', review: 'refresh', probe: 'search', assigned: 'clipboard' };
const due = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : null);

export default function Home() {
  const { profile } = useAuth();
  const { data, error, loading, reload } = useApi<Today>('/today');
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  if (loading && !data) return <div className={s.stack}><Skeleton h={40} w="50%" /><Skeleton h={220} r={22} /><Skeleton h={120} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="We could not load your day" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const step = data.nextStep;

  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>{greet}, {profile?.nickname}</h1><p className={s.lead}>Class {profile?.grade}{profile?.boardId ? ` · ${profile.boardId.toUpperCase()}` : ''}</p></div>

      {step ? (
        <Reveal><section className={s.hero2} aria-label="Your next step">
          <span className={s.kick}>Your next step · about {step.minutes} min</span>
          <h2>{step.title}</h2>
          <div className={s.why}><Icon name={KIND_ICON[step.kind] ?? 'spark'} size={24} accent="#ffd43b" />
            <span>{step.reason}{step.evidenceCount > 0 && <> <em style={{ opacity: .75 }}>(based on {step.evidenceCount} answer{step.evidenceCount === 1 ? '' : 's'})</em></>}</span></div>
          <Button to={step.href} iconRight="arrowR">Start</Button>
        </section></Reveal>
      ) : (
        <Card><EmptyState icon="book" title="Nothing to suggest yet" text="Chapters for your class appear in Learn once a teacher has reviewed them. As soon as one is open, ZENITH will suggest where to start." action={<Button to="/learn" iconRight="arrowR">Open Learn</Button>} /></Card>
      )}

      <div className={s.cols}>
        <Reveal><Card>
          <div className={s.row}><div className={s.ring} style={{ ['--p' as string]: data.xp.progress } as React.CSSProperties}><span>{data.xp.level}</span></div>
            <div><h3>Level {data.xp.level}</h3><p className="muted sm"><CountUp to={data.xp.xp} /> XP · {data.xp.forNext - data.xp.intoLevel} to level {data.xp.level + 1}</p></div></div>
          <p className="sm muted" style={{ marginTop: 10 }}>XP is earned for learning, like first-try answers on new questions and making a topic secure. Repeating a question earns none.</p>
        </Card></Reveal>
        <Reveal delay={80}><Card>
          <div className={s.row}><Icon name="flame" size={34} /><div><h3>{data.streak.days}-day streak</h3>
            <p className="muted sm">{data.streak.activeToday ? 'You have learned today.' : data.streak.days ? 'Learn something today to keep it.' : 'Learn something today to start a streak.'}{data.streak.restDayAvailable && data.streak.days > 0 ? ' One rest day is free this week.' : ''}</p></div></div>
        </Card></Reveal>
      </div>

      <section><h2 style={{ marginBottom: 12 }}>Today’s goals</h2>
        <div className={s.grid}>{data.goals.map((q) => (
          <Card key={q.id} flat><div className={s.between}><span className={s.row} style={{ gap: 8, fontWeight: 700 }}><Icon name={q.icon} size={20} />{q.title}</span><span className="sm muted">{q.done >= q.total ? 'Done' : `${q.done}/${q.total}`}</span></div>
            <div style={{ marginTop: 10 }}><Progress value={(q.done / q.total) * 100} label={q.title} /></div></Card>
        ))}</div>
      </section>

      {data.assigned.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>From your teacher</h2>
          <div className={s.grid}>{data.assigned.map((a) => (
            <Card key={a.id} to={a.href}><div className={s.between}><strong>{a.title}</strong>{due(a.due) && <Chip icon="calendar">Due {due(a.due)}</Chip>}</div>
              {a.note && <p className="sm muted" style={{ marginTop: 6 }}>{a.note}</p>}
              <div style={{ margin: '12px 0 6px' }}><Progress value={(a.done / a.total) * 100} label={a.title} /></div><span className="sm muted">{a.done} of {a.total} done</span></Card>
          ))}</div></section>
      )}

      {data.revision.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Time to revise</h2>
          <Card to="/revision"><div className={s.between}><div><strong>{data.revision.map((r) => r.title).join(', ')}</strong><p className="muted sm">You knew these. A short refresher keeps them.</p></div><Icon name="chevR" size={22} /></div></Card></section>
      )}

      {data.alternatives.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Also recommended</h2>
          <div className={s.grid}>{data.alternatives.map((a) => (
            <Card key={a.href + a.title} to={a.href}><div className={s.row} style={{ gap: 8 }}><Icon name={KIND_ICON[a.kind] ?? 'spark'} size={20} /><strong>{a.title}</strong></div><p className="sm muted" style={{ marginTop: 6 }}>{a.reason}</p></Card>
          ))}</div></section>
      )}

      {data.recent.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>Recent</h2>
          <div className={s.grid}>{data.recent.map((r) => (
            <Card key={r.lessonId} to={`/lesson/${r.lessonId}`}><span className="eyebrow">{r.chapter}</span><h3 style={{ margin: '4px 0' }}>{r.title}</h3><Chip tone={r.status === 'completed' ? 'ok' : 'hi'}>{r.status === 'completed' ? 'Finished' : 'In progress'}</Chip></Card>
          ))}</div></section>
      )}

      <section><div className={s.between}><h2>Milestones</h2><Link to="/progress" className="sm" style={{ fontWeight: 800, textDecoration: 'underline' }}>See My Progress</Link></div>
        <div className={s.grid} style={{ marginTop: 12 }}>{data.milestones.map((m) => (
          <Card key={m.label} flat><span className="muted sm">{m.label}</span><h3 style={{ fontSize: '1.8rem' }}>{m.value}{m.next ? <span className="muted sm" style={{ fontWeight: 600 }}> · next at {m.next}</span> : null}</h3></Card>
        ))}</div></section>
    </div>
  );
}
