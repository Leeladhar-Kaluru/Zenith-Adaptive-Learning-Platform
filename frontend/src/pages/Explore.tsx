import { useApi } from '../api/useApi';
import type { Explore as ExploreData } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const KIND = { simulation: { icon: 'bolt', label: 'Simulation' }, data: { icon: 'chart', label: 'Real data' }, map: { icon: 'globe', label: 'Map' } } as const;

export default function Explore() {
  const { data, error, loading, reload } = useApi<ExploreData>('/explore');
  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Explore</h1><p className={s.lead}>Learn by doing. Everything here opens a real, reviewed lesson you can try right now.</p></div>
      {loading && !data && <Skeleton h={160} r={16} />}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load Explore" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && (<>
        <section><h2 style={{ marginBottom: 12 }}>Revise</h2>
          <div className={s.grid}>{data.available.map((a) => (
            <Reveal key={a.key}><Card to={a.href}><div className={s.row}><Icon name="layers" size={34} /><div><h3>{a.title}</h3><span className="muted sm">{a.count} card{a.count === 1 ? '' : 's'} in reviewed lessons</span></div></div><p className="muted sm" style={{ marginTop: 10 }}>{a.text}</p></Card></Reveal>
          ))}</div></section>
        <section><h2 style={{ marginBottom: 12 }}>Interactive lessons</h2>
          {data.labs.length === 0
            ? <Card><EmptyState icon="book" title="No interactive lessons yet" text="Simulations, charts and maps appear here as soon as a teacher has reviewed a lesson that uses them." action={<Button to="/learn" iconRight="arrowR">Open Learn</Button>} /></Card>
            : <div className={s.grid}>{data.labs.map((l, i) => {
              const k = KIND[l.kind as keyof typeof KIND] ?? KIND.simulation;
              return (
                <Reveal key={l.lessonId} delay={Math.min(i, 8) * 40}><Card to={`/lesson/${l.lessonId}`}>
                  <div className={s.row}><Icon name={k.icon} size={30} /><div><h3>{l.lessonTitle}</h3><span className="muted sm">{l.chapterTitle}</span></div></div>
                  <div className={s.row} style={{ marginTop: 10, gap: 8 }}><Chip tone="soft">{k.label}</Chip><Chip tone="soft">Class {l.grade}</Chip>{l.forYou && <Chip tone="ok" icon="check">For your class</Chip>}</div>
                </Card></Reveal>
              );
            })}</div>}
        </section>
      </>)}
    </div>
  );
}
