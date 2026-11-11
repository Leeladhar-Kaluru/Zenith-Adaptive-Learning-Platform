import { useEffect, useState } from 'react';
import { useApi } from '../api/useApi';
import { useAuth } from '../context/AuthContext';
import { Button, Card, Chip, CountUp, EmptyState, Segmented, Skeleton } from '../ui/kit';
import { ClassQuiz } from './ClassQuiz';
import { BattleRow, type Battle } from './ProfileDash';
import s from './pages.module.css';
import p from './profile.module.css';

interface Arena {
  rating: number; games: number; wins: number; losses: number; draws: number; recent: Battle[];
  classes: Array<{ id: string; name: string; grade: number; subject: string; canPlay: boolean; why: string | null; matchId: string | null; matchStatus: 'waiting' | 'active' | null }>;
}

/** The ranked 1v1 arena: pick a class, find a classmate at your level, play five questions, and see the result in your profile. */
export default function ArenaPage() {
  const { profile } = useAuth();
  const { data, error, loading, reload } = useApi<Arena>('/quiz/arena');
  const [cls, setCls] = useState('');
  useEffect(() => { if (data && !cls) setCls((data.classes.find((c) => c.matchId) ?? data.classes[0])?.id ?? ''); }, [data, cls]);
  const chosen = data?.classes.find((c) => c.id === cls);

  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Arena</h1><p className={s.lead}>Ranked 1v1 quiz battles against classmates at your level. Same five questions for both of you, and faster correct answers score more.</p></div>
      {loading && !data && <Skeleton h={160} r={16} />}
      {error && !data && <EmptyState icon="wifiOff" title="Could not open the Arena" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && (<>
        <div className={p.heroStats}>
          <div className={p.stat}><b><CountUp to={data.rating} /></b><span>quiz rating</span></div>
          <div className={p.stat}><b>{data.wins}</b><span>wins</span></div>
          <div className={p.stat}><b>{data.losses}</b><span>losses</span></div>
          <div className={p.stat}><b>{data.draws}</b><span>draws</span></div>
        </div>
        {data.classes.length === 0 ? (
          <Card><EmptyState icon="people" title="Join a class to play" text="Ranked battles are only between students of the same class, so nobody outside your class sees you. Ask your teacher for a class code and add it in Settings." action={<Button to="/settings" variant="brand">Open Settings</Button>} /></Card>
        ) : (<>
          {data.classes.length > 1 && <Segmented label="Class" value={cls} onChange={setCls} options={data.classes.map((c) => ({ value: c.id, label: c.name }))} />}
          {chosen && !chosen.canPlay && <Card><EmptyState icon="lock" title="You cannot play in this class right now" text={chosen.why ?? ''} action={<Button to="/settings" variant="ghost">Open Settings</Button>} /></Card>}
          {chosen?.canPlay && <ClassQuiz key={chosen.id} classId={chosen.id} avatar={profile?.avatar} nickname={profile?.nickname ?? ''} onDone={reload} />}
        </>)}
        {data.recent.length > 0 && <section><div className={s.between}><h2>Recent battles</h2><Chip tone="soft">{data.games} played</Chip></div>
          <div className={s.stack} style={{ marginTop: 10 }}>{data.recent.map((b) => <BattleRow key={b.id} b={b} />)}</div>
          <p className="sm muted" style={{ marginTop: 8 }}>All your battles are in <a href="/progress?tab=battles" style={{ textDecoration: 'underline', fontWeight: 700 }}>your profile</a>.</p></section>}
      </>)}
    </div>
  );
}
