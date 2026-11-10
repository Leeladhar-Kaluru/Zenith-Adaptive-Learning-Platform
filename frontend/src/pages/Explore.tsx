import { useApi } from '../api/useApi';
import type { Explore as ExploreData } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const ICON: Record<string, string> = { flashcards: 'layers', 'physics-lab': 'bolt', 'chemistry-lab': 'flask', 'biology-lab': 'sprout', 'map-lab': 'globe' };

export default function Explore() {
  const { data, error, loading, reload } = useApi<ExploreData>('/explore');
  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Explore</h1><p className={s.lead}>Learn by doing. We only list what works today; the rest is clearly marked as coming.</p></div>
      {loading && !data && <Skeleton h={160} r={16} />}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load Explore" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && (<>
        <section><h2 style={{ marginBottom: 12 }}>Ready to use</h2>
          <div className={s.grid}>{data.available.map((a) => (
            <Reveal key={a.key}><Card to={a.href}><div className={s.row}><Icon name={ICON[a.key] ?? 'spark'} size={34} /><div><h3>{a.title}</h3><span className="muted sm">{a.count} card{a.count === 1 ? '' : 's'} in reviewed lessons</span></div></div><p className="muted sm" style={{ marginTop: 10 }}>{a.text}</p></Card></Reveal>
          ))}</div></section>
        <section><h2 style={{ marginBottom: 12 }}>In development</h2>
          <div className={s.grid}>{data.planned.map((a, i) => (
            <Reveal key={a.key} delay={i * 60}><Card dashed><div className={s.row}><Icon name={ICON[a.key] ?? 'spark'} size={30} /><div><h3>{a.title}</h3><Chip tone="soft">Not available yet</Chip></div></div><p className="muted sm" style={{ marginTop: 10 }}>{a.text}</p></Card></Reveal>
          ))}</div></section>
      </>)}
    </div>
  );
}
