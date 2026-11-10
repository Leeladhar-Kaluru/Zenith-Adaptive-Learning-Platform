import { useApi } from '../api/useApi';
import type { Today } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, CountUp, EmptyState, Progress, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const KIND_ICON: Record<string, string> = { prereq: 'compass', lesson: 'book', practice: 'target', challenge: 'bolt', review: 'refresh', probe: 'search', assigned: 'clipboard' };

export default function TodayPage() {
  const { profile } = useAuth();
  const { data, error, loading, reload } = useApi<Today>('/today');
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  if (loading && !data) return <div className={s.stack}><Skeleton h={40} w="50%" /><Skeleton h={220} r={22} /><Skeleton h={120} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="We could not load your day" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;

  return (
    <div className={s.stack}>
      <div>
        <h1 className={s.title}>{greet}, {profile?.nickname}</h1>
        <p className={s.lead}>Class {profile?.grade} · CBSE</p>
      </div>

      {data.nextStep ? (
        <Reveal>
          <section className={s.hero2} aria-label="Your next step">
            <span className={s.kick}>Your next step · {data.nextStep.minutes} min</span>
            <h2>{data.nextStep.title}</h2>
            <div className={s.why}><Icon name={KIND_ICON[data.nextStep.kind] ?? 'spark'} size={24} accent="#ffd43b" /><span>{data.nextStep.reason}{data.nextStep.evidenceCount > 0 && <> <em style={{ opacity: .75 }}>(based on {data.nextStep.evidenceCount} answers)</em></>}</span></div>
            <Button to={data.nextStep.href} iconRight="arrowR">Start</Button>
          </section>
        </Reveal>
      ) : (
        <Card><EmptyState icon="book" title="Pick your first lesson" text="Once you answer a few questions, ZENITH will suggest what to do next, and why." action={<Button to="/learn" iconRight="arrowR">Open Learn</Button>} /></Card>
      )}

      <div className={s.cols}>
        <Reveal><Card>
          <div className={s.row}>
            <div className={s.ring} style={{ ['--p' as string]: data.levelProgress } as React.CSSProperties}><span>{data.level}</span></div>
            <div><h3>Level {data.level}</h3><p className="muted sm"><CountUp to={data.xp} /> XP · {Math.round(data.levelProgress)}% to level {data.level + 1}</p></div>
          </div>
        </Card></Reveal>
        <Reveal delay={80}><Card>
          <div className={s.row}><Icon name="flame" size={34} /><div><h3>{data.streak}-day streak</h3><p className="muted sm">Come back tomorrow to keep climbing.</p></div></div>
        </Card></Reveal>
      </div>

      {data.assigned.length > 0 && (
        <section className={s.section}>
          <h2>From your teacher</h2>
          <div className={s.grid}>
            {data.assigned.map((a) => (
              <Card key={a.id} to={a.href}>
                <div className={s.between}><strong>{a.title}</strong><Chip icon="calendar">Due {a.due}</Chip></div>
                <div style={{ margin: '12px 0 6px' }}><Progress value={(a.done / a.total) * 100} label={a.title} /></div>
                <span className="sm muted">{a.done} of {a.total} done</span>
              </Card>
            ))}
          </div>
        </section>
      )}

      {data.recent.length > 0 && (
        <section className={s.section}>
          <h2>Pick up where you left off</h2>
          <div className={s.grid}>
            {data.recent.map((r) => (
              <Card key={r.href} to={r.href}>
                <span className="eyebrow">{r.chapter}</span>
                <h3 style={{ margin: '4px 0 12px' }}>{r.lesson}</h3>
                <Progress value={r.progress} label={r.lesson} />
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
