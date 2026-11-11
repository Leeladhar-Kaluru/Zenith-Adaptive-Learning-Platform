import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { ChatMsg, ChatPage, ChatThread } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, EmptyState, Skeleton } from '../ui/kit';
import { Composer } from './Composer';
import { Message } from './Message';
import { useClassRealtime } from './realtime';
import c from './chat.module.css';

const POLL_LIVE = 30000;   // a safety net while Realtime pings are arriving
const POLL_OFFLINE = 7000; // when Realtime is not available

export function Chat({ classId, isTeacher, onUnread }: { classId: string; isTeacher: boolean; onUnread?: () => void }) {
  const { profile } = useAuth();
  const base = `/classes/${classId}/chat`;
  const [page, setPage] = useState<ChatPage | null>(null);
  const [error, setError] = useState('');
  const [older, setOlder] = useState<ChatMsg[]>([]);
  const [more, setMore] = useState<{ has: boolean; next: string | null }>({ has: false, next: null });
  const [q, setQ] = useState('');
  const [found, setFound] = useState<ChatMsg[] | null>(null);
  const [thread, setThread] = useState<string | null>(null);
  const [replyTo, setReplyTo] = useState<ChatMsg | null>(null);
  const [busyOlder, setBusyOlder] = useState(false);
  const listRef = useRef<HTMLUListElement>(null);
  const stick = useRef(true);

  const load = useCallback(async () => {
    try {
      const p = await api<ChatPage>(`${base}?limit=30`);
      setPage(p); setError('');
      setMore((m) => (older.length ? m : { has: p.hasMore, next: p.next }));
      if (document.visibilityState === 'visible') api(`${base}/read`, { method: 'POST' }).then(() => onUnread?.()).catch(() => {});
    } catch (e) { setError((e as Error).message); }
  }, [base, older.length, onUnread]);

  const live = useClassRealtime(classId, profile?.nickname ?? 'Student', () => void load());
  const changed = useCallback(() => { void load(); live.ping(); if (thread) setThreadTick((t) => t + 1); }, [load, live, thread]);
  const [threadTick, setThreadTick] = useState(0);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const id = window.setInterval(() => { if (document.visibilityState === 'visible') void load(); }, live.connected ? POLL_LIVE : POLL_OFFLINE);
    const onFocus = () => void load();
    window.addEventListener('focus', onFocus);
    return () => { window.clearInterval(id); window.removeEventListener('focus', onFocus); };
  }, [load, live.connected]);

  // keep the newest message in view only if the reader is already at the bottom
  const total = (page?.messages.length ?? 0) + older.length;
  useEffect(() => { const el = listRef.current; if (el && stick.current) el.scrollTop = el.scrollHeight; }, [total, page?.messages[page.messages.length - 1]?.id]);

  useEffect(() => {
    if (!q.trim()) { setFound(null); return; }
    const id = window.setTimeout(() => {
      api<ChatPage>(`${base}?q=${encodeURIComponent(q.trim())}&limit=30`).then((r) => setFound(r.messages.slice().reverse())).catch(() => setFound([]));
    }, 300);
    return () => window.clearTimeout(id);
  }, [q, base]);

  async function loadOlder() {
    if (!more.next) return;
    setBusyOlder(true);
    const el = listRef.current; const prev = el?.scrollHeight ?? 0;
    try {
      const r = await api<ChatPage>(`${base}?limit=30&before=${encodeURIComponent(more.next)}`);
      setOlder((o) => [...r.messages, ...o]);
      setMore({ has: r.hasMore, next: r.next });
      stick.current = false;
      requestAnimationFrame(() => { if (el) el.scrollTop = el.scrollHeight - prev; });
    } catch (e) { setError((e as Error).message); } finally { setBusyOlder(false); }
  }

  if (!page && !error) return <Skeleton h={320} r={16} />;
  if (!page) return <EmptyState icon="wifiOff" title="Could not open the chat" text={error} action={<Button onClick={() => void load()} icon="refresh">Try again</Button>} />;
  const seen = new Set<string>();
  const messages = [...older, ...page.messages].filter((m) => (seen.has(m.id) ? false : (seen.add(m.id), true)));
  const shown = found ?? messages;
  const pinned = page.pinned[0];

  return (
    <section className={c.chat} aria-label="Class chat">
      <div className={c.head}>
        <div className={c.status} role="status">
          <span className={live.connected ? c.dotOn : c.dotOff} aria-hidden="true" />
          {live.connected ? `Live${live.online.length ? ` · ${live.online.length} online` : ''}` : 'Updates every few seconds'}
        </div>
        <label className={c.search}><Icon name="search" size={16} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search messages" aria-label="Search messages" maxLength={60} /></label>
      </div>
      {live.online.length > 0 && <p className={c.online}>Online: {live.online.slice(0, 8).join(', ')}{live.online.length > 8 ? ` +${live.online.length - 8}` : ''}</p>}
      {pinned && !found && (
        <div className={c.pinned}><Icon name="flag" size={16} /><span><strong>{pinned.author.nickname}:</strong> {(pinned.body || pinned.kind).slice(0, 140)}</span>{page.pinned.length > 1 && <em>+{page.pinned.length - 1} more</em>}</div>
      )}
      {thread ? (
        <ThreadView base={base} id={thread} tick={threadTick} canModerate={page.canModerate} isTeacher={isTeacher} muted={page.muted} onClose={() => setThread(null)} onChanged={changed} onTyping={live.typingNow} />
      ) : (<>
        <ul className={c.list} ref={listRef} onScroll={(e) => { const t = e.currentTarget; stick.current = t.scrollHeight - t.scrollTop - t.clientHeight < 80; }} aria-live="polite" aria-label="Messages">
          {!found && more.has && <li className={c.older}><Button size="sm" variant="ghost" loading={busyOlder} onClick={() => void loadOlder()}>Load older messages</Button></li>}
          {found && <li className={c.older}>{found.length} result{found.length === 1 ? '' : 's'} for "{q.trim()}"</li>}
          {shown.length === 0 && <li className={c.empty}>{found ? 'No messages match.' : 'No messages yet. Say hello!'}</li>}
          {shown.map((m) => <Message key={m.id} m={m} base={base} canModerate={page.canModerate} onChanged={changed} onThread={setThread} onReply={setReplyTo} />)}
        </ul>
        {live.typing.length > 0 && <p className={c.typing} role="status">{live.typing.slice(0, 2).join(' and ')} {live.typing.length === 1 ? 'is' : 'are'} typing…</p>}
        <Composer base={base} isTeacher={isTeacher} muted={page.muted} replyTo={replyTo} clearReply={() => setReplyTo(null)} onSent={() => { stick.current = true; changed(); }} onTyping={live.typingNow} />
      </>)}
    </section>
  );
}

function ThreadView({ base, id, tick, canModerate, isTeacher, muted, onClose, onChanged, onTyping }: {
  base: string; id: string; tick: number; canModerate: boolean; isTeacher: boolean; muted: boolean; onClose: () => void; onChanged: () => void; onTyping: () => void;
}) {
  const [t, setT] = useState<ChatThread | null>(null);
  const [err, setErr] = useState('');
  const load = useCallback(() => { api<ChatThread>(`${base}/messages/${id}/thread`).then(setT).catch((e: Error) => setErr(e.message)); }, [base, id]);
  useEffect(() => { load(); }, [load, tick]);
  const after = () => { load(); onChanged(); };
  return (
    <div className={c.thread}>
      <div className={c.threadHead}><Button size="sm" variant="ghost" icon="arrowL" onClick={onClose}>Back to chat</Button><strong>Thread</strong></div>
      {err && <p className={c.err} role="alert">{err}</p>}
      {t && (<>
        <ul className={c.list}>
          <Message m={t.root} base={base} canModerate={canModerate} onChanged={after} inThread />
          {t.messages.map((m) => <Message key={m.id} m={m} base={base} canModerate={canModerate} onChanged={after} inThread />)}
        </ul>
        <Composer base={base} isTeacher={isTeacher} muted={muted} threadId={t.root.id} onSent={after} onTyping={onTyping} />
      </>)}
    </div>
  );
}

/** Teachers: reported messages waiting for a decision. */
export function Reports({ classId, onChanged }: { classId: string; onChanged?: () => void }) {
  const base = `/classes/${classId}/chat`;
  const [rows, setRows] = useState<import('../api/types').ChatReport[] | null>(null);
  const load = useCallback(() => { api<import('../api/types').ChatReport[]>(`${base}/reports`).then(setRows).catch(() => setRows([])); }, [base]);
  useEffect(() => { load(); }, [load]);
  const resolve = (id: string, body: { deleteMessage?: boolean; muteMinutes?: number }) => api(`${base}/reports/${id}/resolve`, { method: 'POST', body }).then(() => { load(); onChanged?.(); });
  if (!rows) return <Skeleton h={80} r={16} />;
  if (rows.length === 0) return <Card><EmptyState icon="check" title="Nothing reported" text="When a student reports a message in this class, it appears here." /></Card>;
  return (
    <div className={c.reports}>{rows.map((r) => (
      <Card key={r.id} flat>
        <p className="sm muted">Reported: {r.reason}</p>
        <p className={c.reported}><strong>{r.message?.author.nickname ?? 'Unknown'}:</strong> {r.message?.removed ? 'Already removed' : r.message?.body || r.message?.kind}</p>
        <div className={c.actionsRow}>
          <Button size="sm" variant="ghost" onClick={() => void resolve(r.id, {})}>Keep message</Button>
          <Button size="sm" variant="danger" icon="trash" onClick={() => void resolve(r.id, { deleteMessage: true })}>Remove</Button>
          <Button size="sm" variant="danger" onClick={() => void resolve(r.id, { deleteMessage: true, muteMinutes: 60 })}>Remove and mute 1 h</Button>
        </div>
      </Card>
    ))}</div>
  );
}
