import { useEffect, useMemo, useState } from 'react';
import { Question } from '../lesson/Question';
import type { Block, PublicItem } from '../api/types';
import { db, listPacks } from '../offline/db';
import { markSeen, pickNext, type Seen } from '../offline/localPractice';
import { pendingCount } from '../offline/sync';
import { Button, Card, Chip, EmptyState, Skeleton } from '../ui/kit';
import s from './pages.module.css';

const SEEN_KEY = 'offline-seen';
type Row = { id: string; difficulty: PublicItem['difficulty']; lessonId: string; item: PublicItem; title: string };

/** Practise from the lessons saved on this device. Works with no network: answers are kept safely and ZENITH marks them and updates your profile when you reconnect. */
export default function OfflinePractice() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [seen, setSeen] = useState<Seen>({});
  const [waiting, setWaiting] = useState(0);
  const [cur, setCur] = useState<Row | null>(null);
  const [done, setDone] = useState(false);
  const [count, setCount] = useState(0);

  useEffect(() => {
    void (async () => {
      const packs = await listPacks();
      const list: Row[] = [];
      for (const p of packs) for (const l of p.lessons) for (const b of l.blocks as Block[]) if (b.kind === 'check') list.push({ id: b.item.id, difficulty: b.item.difficulty, lessonId: l.id, item: b.item, title: l.title });
      const saved = ((await db.snapshots.get(SEEN_KEY).catch(() => undefined))?.data as Seen | undefined) ?? {};
      setSeen(saved); setRows(list); setCur(pickNext(list, saved));
      setWaiting(await pendingCount().catch(() => 0));
    })();
  }, []);
  const byId = useMemo(() => new Map((rows ?? []).map((r) => [r.id, r])), [rows]);

  const next = async () => {
    if (!cur) return;
    const updated = markSeen(seen, cur.id, Date.now());
    setSeen(updated); setCount((c) => c + 1); setDone(false);
    await db.snapshots.put({ key: SEEN_KEY, data: updated, savedAt: new Date().toISOString() }).catch(() => undefined);
    setWaiting(await pendingCount().catch(() => 0));
    setCur(pickNext(rows ?? [], updated, [cur.id]) ?? pickNext(rows ?? [], updated));
  };

  if (!rows) return <Skeleton h={200} r={16} />;
  if (rows.length === 0 || !cur) return <Card><EmptyState icon="download" title="Nothing saved to practise from" text="Save a chapter for offline use first. Its practice questions will be here, with or without internet." action={<Button to="/offline" variant="brand">Open offline lessons</Button>} /></Card>;
  const row = byId.get(cur.id)!;
  return (
    <div className={s.q}>
      <div className={s.between}><div><span className="eyebrow">Offline practice</span><div className="muted sm">{row.title} · question {count + 1}</div></div>
        <Chip tone="soft">{waiting} answer{waiting === 1 ? '' : 's'} waiting to sync</Chip></div>
      <Card key={`${cur.id}-${count}`}>
        <Question item={row.item} context="solve" resetKey={`${cur.id}-${count}`} onResult={() => setDone(true)} />
      </Card>
      <p className="sm muted">Marks and your profile update when you are back online. Questions you have not tried yet come first, easier ones before harder ones.</p>
      {done && <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button variant="brand" iconRight="arrowR" onClick={() => void next()}>Next question</Button></div>}
    </div>
  );
}
