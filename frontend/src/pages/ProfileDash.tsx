import { useEffect, useState } from 'react';
import { useApi } from '../api/useApi';
import { Avatar } from '../icons/Icon';
import { db } from '../offline/db';
import { pendingCount } from '../offline/sync';
import { Button, Card, Chip, CountUp, EmptyState, Skeleton } from '../ui/kit';
import s from './pages.module.css';
import p from './profile.module.css';

export interface Battle {
  id: string; className: string; endedAt: string | null; opponent: { nickname: string; avatar: string | null }; youWon: boolean; draw: boolean; forfeit: boolean;
  myScore: number; theirScore: number; ratingBefore: number; ratingAfter: number;
}
interface Topic { id: string; title: string; subject: string; grade: number; understanding: number; answers: number; correct: number; band: string; confidence: string; practice: string }
interface Dash {
  generatedAt: string; fading: Array<Topic & { recall: number }>;
  me: { nickname: string | null; avatar: string | null; grade: number | null; xp: { level: number; xp: number; into?: number; next?: number }; streak: { days: number } };
  today: { answers: number; correct: number; minutes: number };
  days: Array<{ day: string; answers: number; correct: number; minutes: number }>;
  pace: { answers30d: number; medianMsRight: number | null; medianMsWrong: number | null; hintRate: number | null; guessRate: number | null; byDifficulty: Array<{ level: string; right: number; total: number }> };
  subjects: Array<{ id: string; name: string; topics: number; bands: Record<string, number>; understanding: number; answers: number; accuracy: number | null; rating: number }>;
  focus: Topic[]; strong: Topic[]; revisionDue: number; openMistakes: number;
  battles: { rating: number; games: number; wins: number; draws: number; losses: number; recent: Battle[] };
}

const KEY = 'dashboard';
const BAND_COLOUR: Record<string, string> = { secure: 'var(--ok)', learning: 'var(--brand)', gap_suspected: 'var(--hi, #ffb800)', gap_confirmed: 'var(--gap, #d6455d)', unassessed: 'var(--surface-2)' };
const BAND_NAME: Record<string, string> = { secure: 'Secure', learning: 'Learning', gap_suspected: 'Early signal', gap_confirmed: 'Gap found', unassessed: 'Not enough answers' };
const secs = (ms: number | null) => (ms == null ? '–' : `${(ms / 1000).toFixed(1)} s`);
const pct = (v: number | null) => (v == null ? '–' : `${Math.round(v * 100)}%`);
const ago = (iso: string) => { const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`; };

/** Keeps the dashboard live: refresh when the student answers, when the tab is shown again, when the network returns, and every 20 s while visible. */
function useLive(reload: () => void) {
  useEffect(() => {
    const go = () => { if (document.visibilityState === 'visible') reload(); };
    const id = setInterval(go, 20000);
    addEventListener('zenith:progress', go); addEventListener('focus', go); addEventListener('online', go); document.addEventListener('visibilitychange', go);
    return () => { clearInterval(id); removeEventListener('zenith:progress', go); removeEventListener('focus', go); removeEventListener('online', go); document.removeEventListener('visibilitychange', go); };
  }, [reload]);
}

export function BattleRow({ b }: { b: Battle }) {
  const d = b.ratingAfter - b.ratingBefore;
  return (
    <div className={`${p.battle} ${b.youWon ? p.win : p.loss}`}>
      <Avatar id={b.opponent.avatar ?? undefined} size={34} />
      <div><strong>{b.draw ? 'Draw' : b.youWon ? 'Won' : 'Lost'} vs {b.opponent.nickname}</strong>{b.forfeit && <span className="sm muted"> (someone left)</span>}
        <div className="sm muted">{b.className}{b.endedAt ? ` · ${new Date(b.endedAt).toLocaleDateString()}` : ''}</div></div>
      <span>{b.myScore} – {b.theirScore}</span>
      <span className={`${p.delta} ${d >= 0 ? p.up : p.down}`} aria-label={`Rating change ${d}`}>{d >= 0 ? '+' : ''}{d}</span>
    </div>
  );
}

export function Battles() {
  const { data, error, loading, reload } = useApi<Battle[]>('/quiz/history?limit=50');
  useLive(reload);
  if (loading && !data) return <Skeleton h={200} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load your battles" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data || data.length === 0) return <Card><EmptyState icon="trophy" title="No battles yet" text="Challenge a classmate in the Arena. Every finished battle is kept here with the score and your rating change." action={<Button to="/arena" variant="brand" icon="spark">Open the Arena</Button>} /></Card>;
  return <div className={s.stack}><h2>Your battles</h2>{data.map((b) => <BattleRow key={b.id} b={b} />)}</div>;
}

export function Dashboard() {
  const { data, error, loading, reload } = useApi<Dash>('/profile/dashboard');
  const [cached, setCached] = useState<{ data: Dash; savedAt: string } | null>(null);
  const [waiting, setWaiting] = useState(0);
  const [online, setOnline] = useState(navigator.onLine);
  useLive(reload);
  useEffect(() => { const on = () => setOnline(true), off = () => setOnline(false); addEventListener('online', on); addEventListener('offline', off); return () => { removeEventListener('online', on); removeEventListener('offline', off); }; }, []);
  useEffect(() => { void db.snapshots.get(KEY).then((r) => r && setCached({ data: r.data as Dash, savedAt: r.savedAt })).catch(() => undefined); }, []);
  useEffect(() => { if (data) void db.snapshots.put({ key: KEY, data, savedAt: new Date().toISOString() }).catch(() => undefined); }, [data]);
  useEffect(() => { void pendingCount().then(setWaiting).catch(() => undefined); }, [data, online]);

  const d = data ?? cached?.data ?? null;
  if (!d) {
    if (loading) return <div className={s.stack}><Skeleton h={120} r={16} /><Skeleton h={220} r={16} /></div>;
    return <EmptyState icon="wifiOff" title="Could not load your dashboard" text={error?.message ?? 'You are offline and nothing is saved on this device yet. Open this page once while online.'} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  }
  const stale = !data;
  const max = Math.max(1, ...d.days.map((x) => x.answers));
  const busiest = d.days.reduce((a, b) => (b.answers > a.answers ? b : a), d.days[0]);
  return (
    <div className={s.stack}>
      {(stale || waiting > 0) && <div className={p.banner} role="status">
        {stale ? `You are offline. Showing what was saved ${cached ? ago(cached.savedAt) : ''}.` : ''}{stale && waiting > 0 ? ' ' : ''}{waiting > 0 ? `${waiting} answer${waiting === 1 ? '' : 's'} waiting to sync. They will count here once sent.` : ''}</div>}

      <Card>
        <div className={p.hero}>
          <Avatar id={d.me.avatar ?? undefined} size={72} />
          <div><h2>{d.me.nickname ?? 'You'}</h2><div className="muted">{d.me.grade ? `Class ${d.me.grade} · ` : ''}Level {d.me.xp.level}</div>
            <span className={p.live}><i className={`${p.dot} ${stale ? p.dotOff : ''}`} />{stale ? 'Saved copy' : `Live · updated ${ago(d.generatedAt)}`}</span></div>
          <div className={p.heroStats}>
            <div className={p.stat}><b><CountUp to={d.me.xp.xp} /></b><span>XP</span></div>
            <div className={p.stat}><b>{d.me.streak.days}</b><span>day streak</span></div>
            <div className={p.stat}><b>{d.today.answers}</b><span>answers today · {d.today.answers ? pct(d.today.correct / d.today.answers) : '–'} right</span></div>
            <div className={p.stat}><b>{d.battles.rating}</b><span>quiz rating · {d.battles.wins}W {d.battles.losses}L {d.battles.draws}D</span></div>
          </div>
        </div>
      </Card>

      <section><h2 style={{ marginBottom: 10 }}>Last 14 days</h2>
        <Card>
          {d.days.every((x) => x.answers === 0) ? <EmptyState icon="target" title="No answers in the last two weeks" text="Practise for a few minutes and your daily bars will appear." action={<Button to="/practice" variant="brand">Practise now</Button>} /> : (<>
            <div className={p.bars} role="img" aria-label="Questions answered each day for the last 14 days">
              {d.days.map((x) => (
                <div key={x.day} className={p.barCol} title={`${x.day}: ${x.correct} of ${x.answers} right · ${x.minutes} min`}>
                  <div className={p.bar} style={{ height: `${Math.max(3, (x.answers / max) * 100)}%` }}><div className={p.barOk} style={{ height: `${x.answers ? (x.correct / x.answers) * 100 : 0}%` }} /></div>
                </div>))}
            </div>
            <div className={p.axis} aria-hidden="true">{d.days.map((x, i) => <span key={x.day}>{i % 2 === 0 ? x.day.slice(8) : ''}</span>)}</div>
            <p className="sm muted" style={{ marginTop: 8 }}>Green is right answers, the bar is all answers. Busiest day: {busiest.day} with {busiest.answers}. About {Math.round(d.days.reduce((a, x) => a + x.minutes, 0))} minutes in total.</p></>)}
        </Card></section>

      <section><h2 style={{ marginBottom: 10 }}>By subject</h2>
        {d.subjects.length === 0 ? <Card><EmptyState icon="peak" title="Nothing measured yet" text="Answer questions in a lesson or in Practice and each subject will show how well you understand it." /></Card> : (
          <div className={p.grid}>{d.subjects.map((x) => {
            const total = Math.max(1, x.topics);
            return (
              <Card key={x.id} flat>
                <div className={s.between}><strong>{x.name}</strong><Chip tone="soft">{x.answers < 5 ? 'Just started' : `${Math.round(x.understanding * 100)}% understood`}</Chip></div>
                <div className={p.stack2} style={{ marginTop: 10 }} role="img" aria-label={`${x.name} topics by status`}>
                  {Object.entries(x.bands).map(([b, n]) => <i key={b} style={{ width: `${(n / total) * 100}%`, background: BAND_COLOUR[b] ?? 'var(--surface-2)' }} title={`${BAND_NAME[b] ?? b}: ${n}`} />)}</div>
                <div className={p.legend}>{Object.entries(x.bands).map(([b, n]) => <span key={b}><i style={{ background: BAND_COLOUR[b] }} />{BAND_NAME[b] ?? b} {n}</span>)}</div>
                <p className="sm muted" style={{ marginTop: 8 }}>{x.answers} answer{x.answers === 1 ? '' : 's'} · {pct(x.accuracy)} right · subject rating {x.rating}</p>
                <Button to={`/practice?subject=${x.id}`} size="sm" variant="ghost" icon="target">Practise {x.name}</Button>
              </Card>);
          })}</div>)}
      </section>

      <div className={p.grid}>
        <Card><h3>Work on next</h3>
          {d.focus.length === 0 ? <p className="muted sm" style={{ marginTop: 8 }}>No weak topics found yet. Topics appear here after at least three answers.</p> : d.focus.map((t) => (
            <div key={t.id} className={s.between} style={{ marginTop: 10 }}><div><strong>{t.title}</strong><div className="sm muted">{t.correct} of {t.answers} right · {Math.round(t.understanding * 100)}% · confidence {t.confidence}</div></div><Button to={t.practice} size="sm" variant="brand">Practise</Button></div>))}
          <div style={{ marginTop: 12 }}><Button to="/check" size="sm" variant="ghost" icon="compass">Take an adaptive check</Button></div>
        </Card>
        {d.fading.length > 0 && <Card><h3>Fading from memory</h3>
          {d.fading.map((t) => <div key={t.id} className={s.between} style={{ marginTop: 10 }}><div><strong>{t.title}</strong><div className="sm muted">You knew this well, but it may be fading: about {Math.round(t.recall * 100)}% likely to be remembered now.</div></div><Button to={t.practice} size="sm" variant="ghost">Refresh</Button></div>)}
          <p className="sm muted" style={{ marginTop: 10 }}>A simple forgetting-curve estimate from how much you practised and how long ago.</p></Card>}
        <Card><h3>Your strengths</h3>
          {d.strong.length === 0 ? <p className="muted sm" style={{ marginTop: 8 }}>Topics you know well show up here.</p> : d.strong.map((t) => (
            <div key={t.id} style={{ marginTop: 10 }}><strong>{t.title}</strong><div className="sm muted">{t.correct} of {t.answers} right · {Math.round(t.understanding * 100)}%</div></div>))}
          <p className="sm muted" style={{ marginTop: 12 }}>{d.revisionDue} revision card{d.revisionDue === 1 ? '' : 's'} due · {d.openMistakes} mistake group{d.openMistakes === 1 ? '' : 's'} to fix</p>
        </Card>
        <Card><h3>How you work</h3>
          {d.pace.answers30d === 0 ? <p className="muted sm" style={{ marginTop: 8 }}>Your pace shows after you answer some questions.</p> : (<ul className="sm" style={{ paddingLeft: 18, margin: '8px 0 0', lineHeight: 1.7 }}>
            <li>Right answers take about {secs(d.pace.medianMsRight)}; wrong ones about {secs(d.pace.medianMsWrong)}.</li>
            <li>You used hints on {pct(d.pace.hintRate)} of answers.</li>
            {(d.pace.guessRate ?? 0) > 0.05 && <li>{pct(d.pace.guessRate)} were wrong answers under 2 seconds, which look like guesses. Slow down on those.</li>}
            {d.pace.byDifficulty.map((x) => <li key={x.level}>{x.level === 'intro' ? 'Warm-up' : x.level === 'challenge' ? 'Challenge' : 'Standard'} questions: {x.right} of {x.total} right ({pct(x.right / x.total)}).</li>)}
          </ul>)}
          <p className="sm muted" style={{ marginTop: 10 }}>Based on your last 30 days of answers.</p>
        </Card>
        <Card><h3>Arena</h3>
          <p className="muted sm" style={{ marginTop: 6 }}>{d.battles.games} battle{d.battles.games === 1 ? '' : 's'} · rating <b>{d.battles.rating}</b></p>
          {d.battles.recent.slice(0, 3).map((b) => <div key={b.id} style={{ marginTop: 8 }}><BattleRow b={b} /></div>)}
          <div style={{ marginTop: 12 }}><Button to="/arena" size="sm" variant="brand" icon="spark">{d.battles.games ? 'Play again' : 'Play your first battle'}</Button></div>
        </Card>
      </div>
      <Button variant="ghost" size="sm" icon="refresh" onClick={reload}>Refresh now</Button>
    </div>
  );
}
