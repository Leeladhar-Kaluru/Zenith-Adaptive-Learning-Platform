import { useState } from 'react';
import { api } from '../api/client';
import type { ChatMsg } from '../api/types';
import { Avatar, Icon } from '../icons/Icon';
import { Button, Chip, useToast } from '../ui/kit';
import c from './chat.module.css';

export const REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🎉', '👏', '🔥', '💡', '🤔', '✅', '🙏'];
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { hour: 'numeric', minute: '2-digit', ...(Date.now() - new Date(iso).getTime() > 864e5 ? { day: 'numeric', month: 'short' } : {}) });
const size = (n?: number) => (n ? (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`) : '');

/** Pictures need a short-lived link from the API (the bucket is private), fetched when the picture scrolls into view. */
function Attachment({ base, m }: { base: string; m: ChatMsg }) {
  const a = m.attachment!;
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const open = async () => {
    try { const r = await api<{ url: string }>(`${base}/messages/${m.id}/file`); setUrl(r.url); return r.url; } catch (e) { setErr((e as Error).message); return null; }
  };
  if (m.kind === 'gif' && a.url) return <figure className={c.media}><img src={a.url} alt={a.title || 'GIF'} loading="lazy" referrerPolicy="no-referrer" /><figcaption>GIF · GIPHY</figcaption></figure>;
  if (m.kind === 'image') {
    return url
      ? <figure className={c.media}><a href={url} target="_blank" rel="noopener noreferrer"><img src={url} alt={a.name || 'Picture'} loading="lazy" /></a></figure>
      : <button className={c.fileBtn} onClick={() => void open()}><Icon name="image" size={18} /> {a.name} · {size(a.size)} <span>Show picture</span></button>;
  }
  return (
    <div>
      <button className={c.fileBtn} onClick={async () => { const u = await open(); if (u) window.open(u, '_blank', 'noopener'); }}><Icon name="download" size={18} /> {a.name} · {size(a.size)} <span>Open</span></button>
      {err && <p className={c.err} role="alert">{err}</p>}
    </div>
  );
}

export function Message({ m, base, canModerate, onChanged, onThread, onReply, inThread }: {
  m: ChatMsg; base: string; canModerate: boolean; onChanged: () => void; onThread?: (id: string) => void; onReply?: (m: ChatMsg) => void; inThread?: boolean;
}) {
  const toast = useToast();
  const [more, setMore] = useState(false);
  const [picker, setPicker] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState('');
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    try { await fn(); if (ok) toast(ok, 'ok'); onChanged(); } catch (e) { toast((e as Error).message, 'err'); }
  };
  const react = (emoji: string) => { setPicker(false); void run(() => api(`${base}/messages/${m.id}/reaction`, { method: 'PUT', body: { emoji } })); };

  if (m.removed) return <li className={c.row}><p className={c.gone}>This message was removed.</p></li>;
  const mine = m.author.me;
  return (
    <li className={`${c.row} ${mine ? c.mine : ''} ${m.kind === 'announcement' ? c.notice : ''}`}>
      {!mine && <Avatar id={m.author.avatar} size={34} />}
      <div className={c.bubbleCol}>
        <div className={c.who}>
          <strong>{mine ? 'You' : m.author.nickname}</strong>
          {m.author.teacher && <Chip tone="hi">Teacher</Chip>}
          {m.kind === 'announcement' && <Chip tone="hi" icon="bell">Announcement</Chip>}
          {m.pinned && <Chip tone="soft" icon="flag">Pinned</Chip>}
          <time dateTime={m.createdAt}>{when(m.createdAt)}</time>
        </div>
        <div className={c.bubble}>
          {m.replyTo && <div className={c.quote}><strong>{m.replyTo.nickname}</strong> {m.replyTo.snippet}</div>}
          {m.kind === 'poll' && m.poll ? (
            <div className={c.poll}>
              <strong>{m.body}</strong>
              {m.poll.options.map((o, i) => {
                const pct = m.poll!.total ? Math.round((o.votes / m.poll!.total) * 100) : 0;
                return (
                  <button key={i} className={c.opt} aria-pressed={m.poll!.myVote === i} onClick={() => void run(() => api(`${base}/messages/${m.id}/vote`, { method: 'PUT', body: { option: i } }))}>
                    <span className={c.bar} style={{ width: `${pct}%` }} aria-hidden="true" /><span className={c.optText}>{o.text}</span><span className={c.optN}>{o.votes} · {pct}%</span>
                  </button>
                );
              })}
              <span className="sm muted">{m.poll.total} vote{m.poll.total === 1 ? '' : 's'}. You can change your vote.</span>
            </div>
          ) : (<>
            {m.attachment && <Attachment base={base} m={m} />}
            {m.body && m.kind !== 'gif' && <p className={c.text}>{m.body}</p>}
          </>)}
        </div>
        {m.reactions.length > 0 && (
          <div className={c.reacts}>{m.reactions.map((r) => <button key={r.emoji} className={c.react} aria-pressed={r.mine} aria-label={`${r.emoji} ${r.count}`} onClick={() => react(r.emoji)}>{r.emoji} {r.count}</button>)}</div>
        )}
        <div className={c.actions}>
          <button onClick={() => setPicker((v) => !v)} aria-expanded={picker} aria-label="Add a reaction">☺ React</button>
          {onReply && <button onClick={() => onReply(m)}>Reply</button>}
          {!inThread && onThread && <button onClick={() => onThread(m.id)}>{m.threadCount ? `Thread (${m.threadCount})` : 'Thread'}</button>}
          <button onClick={() => setMore((v) => !v)} aria-expanded={more} aria-label="More actions">⋯</button>
        </div>
        {picker && <div className={c.picker} role="group" aria-label="Reactions">{REACTIONS.map((e) => <button key={e} onClick={() => react(e)} aria-label={`React ${e}`}>{e}</button>)}</div>}
        {more && (
          <div className={c.more} role="group" aria-label="Message actions">
            {canModerate && !inThread && <Button size="sm" variant="ghost" onClick={() => void run(() => api(`${base}/messages/${m.id}/pin`, { method: 'PUT', body: { pinned: !m.pinned } }), m.pinned ? 'Unpinned' : 'Pinned')}>{m.pinned ? 'Unpin' : 'Pin'}</Button>}
            {(mine || canModerate) && <Button size="sm" variant="danger" icon="trash" onClick={() => void run(() => api(`${base}/messages/${m.id}`, { method: 'DELETE' }), 'Removed')}>Remove</Button>}
            {!mine && <Button size="sm" variant="ghost" onClick={() => setReporting(true)}>Report</Button>}
            {!mine && !canModerate && !m.author.teacher && <Button size="sm" variant="ghost" onClick={() => void run(() => api(`${base}/messages/${m.id}/block`, { method: 'POST' }), `You will not see ${m.author.nickname} any more`)}>Block</Button>}
            {!mine && canModerate && <Button size="sm" variant="ghost" onClick={() => void run(() => api(`${base}/messages/${m.id}/mute`, { method: 'POST', body: { minutes: 60 } }), `${m.author.nickname} is muted for an hour`)}>Mute 1 h</Button>}
          </div>
        )}
        {reporting && (
          <form className={c.report} onSubmit={(e) => { e.preventDefault(); void run(() => api(`${base}/messages/${m.id}/report`, { method: 'POST', body: { reason } }), 'Thank you. Your teacher will look at it.').then(() => { setReporting(false); setReason(''); setMore(false); }); }}>
            <label>What is wrong with this message?<input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} autoFocus /></label>
            <div className={c.actionsRow}><Button size="sm" variant="brand" disabled={!reason.trim()} type="submit">Send report</Button><Button size="sm" variant="ghost" type="button" onClick={() => setReporting(false)}>Cancel</Button></div>
          </form>
        )}
      </div>
    </li>
  );
}
