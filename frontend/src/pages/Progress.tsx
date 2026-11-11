import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import type { Band, Gamification, Notebook, Overview } from '../api/types';
import { Avatar, Icon, TierBadge } from '../icons/Icon';
import { TIERS } from '../icons/icons.mjs';
import { Button, Card, Chip, CountUp, EmptyState, Progress as Bar, Reveal, Segmented, Skeleton } from '../ui/kit';
import { GapMap } from './GapMap';
import { Battles, Dashboard } from './ProfileDash';
import s from './pages.module.css';

const TONE: Record<Band, 'ok' | 'hi' | 'gap' | 'soft'> = { secure: 'ok', learning: 'hi', gap_confirmed: 'gap', gap_suspected: 'hi', unassessed: 'soft' };
const NAME: Record<Band, string> = { secure: 'Secure', learning: 'Learning', gap_confirmed: 'Gap found', gap_suspected: 'Early signal', unassessed: 'Not enough answers yet' };
const OFF = {
  no_classroom: 'Leagues are for classmates. Join your teacher’s class with a class code in Settings to play.',
  teacher_off: 'Your teacher has switched leagues off for this class. Goals and badges still count.',
  opted_out: 'You have hidden yourself from the league. You can turn it back on in Settings.',
  too_few: 'The league starts when at least two classmates are in it.',
} as const;
const left = (iso: string) => { const d = Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 864e5)); return d ? `resets in ${d} day${d > 1 ? 's' : ''}` : 'resets today'; };

function Understanding() {
  const { data, error, loading, reload } = useApi<Overview>('/progress/overview');
  if (loading && !data) return <div className={s.stack}><Skeleton h={120} r={16} /><Skeleton h={220} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load your progress" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const max = Math.max(1, ...data.activity.map((a) => a.answers));
  return (
    <div className={s.stack}>
      <div className={s.cols}>
        <Card><span className="muted sm">Level</span><h3 style={{ fontSize: '2rem' }}>{data.xp.level}</h3><span className="muted sm"><CountUp to={data.xp.xp} /> XP</span></Card>
        <Card><span className="muted sm">Streak</span><h3 style={{ fontSize: '2rem' }}>{data.streak.days} days</h3><span className="muted sm">{data.streak.restDayAvailable ? 'One rest day is free this week' : 'Rest day used this week'}</span></Card>
        <Card><span className="muted sm">To revisit</span><h3 style={{ fontSize: '2rem' }}>{data.mistakes + data.revisionDue}</h3><span className="muted sm">{data.mistakes} mistakes · {data.revisionDue} due for revision</span></Card>
      </div>

      <GapMap />

      <section><h2 style={{ marginBottom: 12 }}>What you understand</h2>
        {data.concepts.length === 0 ? <Card><EmptyState icon="target" title="Nothing measured yet" text="Answer a few questions in a lesson or in Practice. ZENITH will show what you understand here, and how sure it is." action={<Button to="/practice" variant="brand">Start practising</Button>} /></Card> : (
          <div className={s.stack}>{data.concepts.map((c) => (
            <Card key={c.id} flat><div className={s.between}><div><strong>{c.title}</strong><div className="sm muted">Class {c.grade} · {c.correct} of {c.evidence} right · confidence {c.confidence} · level {c.level}</div></div><Chip tone={TONE[c.band]}>{NAME[c.band]}</Chip></div>
              <div style={{ marginTop: 10 }}><Bar value={c.pKnown * 100} label={`${c.title} understanding`} /></div></Card>
          ))}</div>
        )}
        <p className="sm muted" style={{ marginTop: 10 }}><Icon name="info" size={16} /> The bar is an estimate from your answers. It gets more reliable as you answer more questions on different problems.</p>
      </section>

      {data.chapters.length > 0 && <section><h2 style={{ marginBottom: 12 }}>Chapters</h2><div className={s.grid}>{data.chapters.map((c) => (
        <Card key={c.slug} to={`/learn/${c.slug}`}><span className="eyebrow">{c.subject}</span><h3>{c.title}</h3><p className="sm muted" style={{ margin: '6px 0 10px' }}>{c.lessonsDone} of {c.lessons} lessons · {c.concepts.secure ?? 0} of {c.conceptTotal} topics secure</p><Bar value={(c.lessonsDone / Math.max(1, c.lessons)) * 100} label={c.title} /></Card>
      ))}</div></section>}

      {data.activity.length > 0 && <section><h2 style={{ marginBottom: 12 }}>Last 4 weeks</h2><Card>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 110 }} role="img" aria-label="Questions answered each day">
          {data.activity.map((a) => <div key={a.day} title={`${a.day}: ${a.correct}/${a.answers} right`} style={{ flex: 1, minWidth: 6, height: `${Math.max(8, (a.answers / max) * 100)}%`, background: 'var(--brand)', border: '2px solid var(--ink)', borderRadius: 6 }} />)}
        </div><p className="sm muted" style={{ marginTop: 8 }}>Each bar is a day you answered questions.</p></Card></section>}
    </div>
  );
}

function Achievements() {
  const { data, error, loading, reload } = useApi<Gamification>('/gamification');
  if (loading && !data) return <Skeleton h={320} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load achievements" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const lg = data.league;
  return (
    <div className={s.stack}>
      <div className={s.cols}>
        <Card>
          {lg ? (<>
            <div className={s.between}><h3>{TIERS.find((t) => t.id === lg.tier)?.name} league · {lg.classroom}</h3><Chip>{left(lg.endsAt)}</Chip></div>
            <p className="sm muted">Ranked by XP earned this week. Only nicknames and characters are shown.</p>
            <div className={s.tiers}>{TIERS.map((t) => <div key={t.id} className={s.tierC}><TierBadge tier={t.id} size={44} active={t.id === lg.tier} />{t.name}</div>)}</div>
            {lg.rows.map((r, i) => (<div key={r.rank}>
              {(i === 0 || lg.rows[i - 1].zone !== r.zone) && <div className={`${s.zone} ${r.zone === 'up' ? s.up : r.zone === 'down' ? s.dn : ''}`}>{r.zone === 'up' ? 'Moves up' : r.zone === 'down' ? 'Moves down' : 'Stays'}</div>}
              <div className={`${s.lr} ${r.me ? s.me : ''}`}><span className={s.rk}>{r.rank}</span><Avatar id={r.avatar} size={36} /><span>{r.me ? 'You' : r.nickname}</span><span className={s.xp2}>{r.xp}</span></div></div>))}
          </>) : <EmptyState icon="people" title="No league yet" text={OFF[data.reason ?? 'no_classroom']} action={<Button to="/settings" variant="ghost" size="sm">Open Settings</Button>} />}
        </Card>
        <Card><h3>Today’s goals</h3><div className={s.stack} style={{ marginTop: 14 }}>{data.quests.map((q) => (
          <div key={q.id}><div className={s.between}><span className={s.row} style={{ gap: 8, fontWeight: 700 }}><Icon name={q.icon} size={20} />{q.title}</span><span className="sm muted">{q.done >= q.total ? 'Done' : `${q.done}/${q.total}`}</span></div><div style={{ marginTop: 6 }}><Bar value={(q.done / q.total) * 100} label={q.title} /></div></div>
        ))}</div></Card>
      </div>
      <section><h2 style={{ marginBottom: 12 }}>Badges</h2><div className={s.badges}>{data.badges.map((b, i) => (
        <Reveal key={b.id} delay={i * 50}><div className={`${s.bdg} ${b.earned ? '' : s.bdgOff}`}><div className={s.bdgIcon}><Icon name={b.earned ? b.icon : 'lock'} size={30} /></div><strong>{b.title}</strong><span className="sm muted">{b.hint}</span></div></Reveal>
      ))}</div></section>
    </div>
  );
}

function Mistakes() {
  const [all, setAll] = useState(false);
  const { data, error, loading, reload } = useApi<Notebook>(`/progress/notebook${all ? '?resolved=true' : ''}`);
  return (
    <div className={s.stack}>
      <div className={s.between}><div><h2>Mistake notebook</h2><p className="muted sm">Your mistakes grouped by the idea behind them. A group closes when you get that topic right three times in a row.</p></div>
        <Segmented label="Show" value={all ? 'all' : 'open'} onChange={(v) => setAll(v === 'all')} options={[{ value: 'open', label: 'To fix' }, { value: 'all', label: 'All' }]} /></div>
      {loading && !data && <Skeleton h={160} r={16} />}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && data.groups.length === 0 && <Card><EmptyState icon="check" title={all ? 'No mistakes yet' : 'Nothing to fix'} text="When you slip on a question, the idea behind it collects here with a chance to try a fresh question." /></Card>}
      {data?.groups.map((g) => (
        <Card key={g.code + g.concept.id} flat>
          <div className={s.between}><strong>{g.misconception}</strong><Chip tone={g.resolved ? 'ok' : 'gap'}>{g.resolved ? 'Fixed' : `${g.times} time${g.times === 1 ? '' : 's'}`}</Chip></div>
          <p className="sm muted" style={{ marginTop: 4 }}>Topic: {g.concept.title}</p>
          {g.examples.map((e, i) => <div key={i} style={{ marginTop: 10 }}><div className="sm"><strong>Example:</strong> {e.stem}</div><div className="sm muted">{e.explanation}</div></div>)}
          {!g.resolved && <div style={{ marginTop: 12 }}><Button to={g.practice} size="sm" variant="brand" icon="target">Try a fresh question</Button></div>}
        </Card>
      ))}
    </div>
  );
}

export default function Progress() {
  type Tab = 'dashboard' | 'understanding' | 'battles' | 'achievements' | 'mistakes';
  const [params] = useSearchParams();
  const first = params.get('tab');
  const [tab, setTab] = useState<Tab>((['dashboard', 'understanding', 'battles', 'achievements', 'mistakes'] as const).find((t) => t === first) ?? 'dashboard');
  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>My Profile</h1><p className={s.lead}>How you are doing, what you understand, your battles and what to fix. Every number comes from your real answers and updates as you learn.</p></div>
      <Segmented label="Section" value={tab} onChange={setTab} options={[{ value: 'dashboard', label: 'Dashboard' }, { value: 'understanding', label: 'Understanding' }, { value: 'battles', label: 'Battles' }, { value: 'achievements', label: 'Achievements' }, { value: 'mistakes', label: 'Mistakes' }]} />
      {tab === 'dashboard' && <Dashboard />}{tab === 'battles' && <Battles />}{tab === 'understanding' && <Understanding />}{tab === 'achievements' && <Achievements />}{tab === 'mistakes' && <Mistakes />}
      <p className="sm muted"><Link to="/revision" style={{ textDecoration: 'underline', fontWeight: 700 }}>Revision cards</Link> bring back topics you knew, just before you might forget them.</p>
    </div>
  );
}
