import { useApi } from '../api/useApi';
import type { Climb } from '../api/types';
import { Avatar, Icon, TierBadge } from '../icons/Icon';
import { TIERS } from '../icons/icons.mjs';
import { Button, Card, EmptyState, Progress, Reveal, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const OFF: Record<string, string> = {
  no_classroom: 'Leagues are for classmates. Join your teacher’s class with a class code to compete with friends.',
  teacher_off: 'Your teacher has switched leagues off for this class. Quests and badges still count.',
  opted_out: 'You have hidden yourself from the league. You can turn it back on in Settings.',
};

function daysLeft(iso: string) {
  const d = Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 864e5));
  return d === 0 ? 'resets today' : `resets in ${d} day${d > 1 ? 's' : ''}`;
}

export default function ClimbPage() {
  const { data, error, loading, reload } = useApi<Climb>('/climb');
  if (loading && !data) return <div className={s.stack}><Skeleton h={44} w="30%" /><Skeleton h={300} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load Climb" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const lg = data.league;

  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Climb</h1><p className={s.lead}>Ranked by growth, so improving beats grinding.</p></div>
      <div className={s.cols}>
        <Reveal><Card>
          {lg ? (<>
            <div className={s.between}><h3>{TIERS.find((t) => t.id === lg.tier)?.name} league</h3><span className="chip" style={{ fontSize: '.8rem' }}>{daysLeft(lg.endsAt)}</span></div>
            <div className={s.tiers}>{TIERS.map((t) => <div key={t.id} className={s.tierC}><TierBadge tier={t.id} size={48} active={t.id === lg.tier} />{t.name}</div>)}</div>
            {lg.rows.map((r, i) => (
              <div key={r.rank}>
                {(i === 0 || lg.rows[i - 1].zone !== r.zone) && <div className={`${s.zone} ${r.zone === 'up' ? s.up : r.zone === 'down' ? s.dn : ''}`}>{r.zone === 'up' ? 'Moves up' : r.zone === 'down' ? 'Moves down' : 'Stays'}</div>}
                <div className={`${s.lr} ${r.me ? s.me : ''}`}><span className={s.rk}>{r.rank}</span><Avatar id={r.avatar} size={36} /><span>{r.me ? 'You' : r.nickname}</span><span className={s.xp2}>{r.xp}</span></div>
              </div>
            ))}
          </>) : <EmptyState icon="people" title="No league yet" text={OFF[data.leagueDisabledReason ?? 'no_classroom']} action={<Button to="/settings" variant="ghost" size="sm">Open Settings</Button>} />}
        </Card></Reveal>

        <div className={s.stack}>
          {data.goal && <Reveal delay={80}><Card><h3>Class goal</h3><p className="muted sm" style={{ margin: '4px 0 12px' }}>{data.goal.title}</p><Progress value={data.goal.percent} label="Class goal" /><p className="hand" style={{ marginTop: 8 }}>{data.goal.percent}% there. Finish today’s quest to help!</p></Card></Reveal>}
          <Reveal delay={140}><Card>
            <div className={s.between}><h3>Today’s quests</h3><span className="sm muted">{data.streak.days}-day streak{data.streak.restDayAvailable ? ' · 1 rest day left' : ''}</span></div>
            <div className={s.stack} style={{ marginTop: 14 }}>
              {data.quests.map((q) => (
                <div key={q.id}><div className={s.between}><span className={s.row} style={{ gap: 8, fontWeight: 700 }}><Icon name={q.icon} size={20} />{q.title}</span><span className="sm muted">{q.done >= q.total ? 'Done' : `${q.done}/${q.total}`}</span></div><div style={{ marginTop: 6 }}><Progress value={(q.done / q.total) * 100} label={q.title} /></div></div>
              ))}
            </div>
          </Card></Reveal>
        </div>
      </div>

      <section className={s.section}>
        <h2>Badges</h2>
        <div className={s.badges}>
          {data.badges.map((b, i) => (
            <Reveal key={b.id} delay={i * 50}><div className={`${s.bdg} ${b.earned ? '' : s.bdgOff}`}>
              <div className={s.bdgIcon}><Icon name={b.earned ? b.icon : 'lock'} size={30} /></div>
              <strong>{b.title}</strong><span className="sm muted">{b.hint}</span>
            </div></Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
