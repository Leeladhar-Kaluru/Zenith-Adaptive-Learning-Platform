import { useEffect, useRef, useState } from 'react';
import { api, API_BASE } from '../api/client';
import { uploadFile } from '../api/upload';
import type { ChatMsg, Gif } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, useToast } from '../ui/kit';
import c from './chat.module.css';

const EMOJI = '😀 😃 😄 😁 😆 😅 😂 🙂 😉 😊 😍 🤩 😎 🤔 😮 😢 😭 😡 🥳 🤗 🙌 👍 👏 🙏 💪 🎉 🎯 ⭐ 🔥 💡 ✅ ❌ ❤️ 💙 📚 ✏️ 🧪 🔬 🌍 ⚡ 🧮 🧠 🏆 🌟 😴 🤝 👋 🍎 ☀️ 🌈'.split(' ');
const ACCEPT = 'image/png,image/jpeg,image/gif,image/webp,application/pdf';
const MAX = 4 * 1024 * 1024;

function GifPicker({ base, onPick, onClose }: { base: string; onPick: (g: Gif) => void; onClose: () => void }) {
  const [q, setQ] = useState('');
  const [gifs, setGifs] = useState<Gif[] | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    const id = window.setTimeout(() => {
      api<{ gifs: Gif[] }>(`${base}/gifs?q=${encodeURIComponent(q)}`).then((r) => { setGifs(r.gifs); setErr(''); }).catch((e: Error) => { setGifs([]); setErr(e.message); });
    }, q ? 350 : 0);
    return () => window.clearTimeout(id);
  }, [q, base]);
  return (
    <div className={c.panel} role="dialog" aria-label="Choose a GIF">
      <div className={c.panelHead}><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search GIFs" aria-label="Search GIFs" maxLength={60} autoFocus /><button onClick={onClose} aria-label="Close GIFs"><Icon name="close" size={18} /></button></div>
      {err ? <p className={c.err} role="alert">{err}</p> : gifs === null ? <p className="muted sm">Loading…</p> : gifs.length === 0 ? <p className="muted sm">No GIFs found.</p> : (
        <div className={c.gifs}>{gifs.map((g) => <button key={g.id} onClick={() => onPick(g)} aria-label={g.title}><img src={g.preview} alt="" loading="lazy" referrerPolicy="no-referrer" /></button>)}</div>
      )}
      <p className="sm muted">Powered by GIPHY. Family-friendly (G) only.</p>
    </div>
  );
}

export function Composer({ base, isTeacher, muted, threadId, replyTo, clearReply, onSent, onTyping }: {
  base: string; isTeacher: boolean; muted: boolean; threadId?: string; replyTo?: ChatMsg | null; clearReply?: () => void; onSent: () => void; onTyping?: () => void;
}) {
  const toast = useToast();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [panel, setPanel] = useState<'' | 'emoji' | 'gif' | 'poll'>('');
  const [progress, setProgress] = useState<number | null>(null);
  const [announce, setAnnounce] = useState(false);
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);
  const ctl = useRef<AbortController | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const done = () => { setText(''); setPanel(''); setAnnounce(false); clearReply?.(); onSent(); };
  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try { await fn(); done(); } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  };
  const send = () => text.trim() && guard(() => api(`${base}/messages`, { method: 'POST', body: { text, replyTo: replyTo?.id, threadId, announcement: announce } }));
  const pickFile = async (f?: File) => {
    if (!f) return;
    if (f.size > MAX) { toast('That file is too big. The limit is 4 MB.', 'err'); return; }
    ctl.current = new AbortController();
    setProgress(0);
    try {
      const qs = new URLSearchParams({ name: f.name, caption: text.slice(0, 200), ...(threadId ? { threadId } : {}) });
      await uploadFile<ChatMsg>(`${API_BASE}${base}/upload?${qs}`, f, setProgress, ctl.current.signal);
      done();
    } catch (e) { toast((e as Error).message, 'err'); } finally { setProgress(null); if (fileRef.current) fileRef.current.value = ''; }
  };

  if (muted) return <p className={c.mutedNote} role="status">Your teacher has paused your chat for now. You can still read everything.</p>;
  return (
    <div className={c.composer}>
      {replyTo && <div className={c.replying}>Replying to <strong>{replyTo.author.nickname}</strong>: {(replyTo.body || replyTo.kind).slice(0, 60)}<button onClick={clearReply} aria-label="Cancel reply"><Icon name="close" size={16} /></button></div>}
      {progress !== null && (
        <div className={c.progress} role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Uploading">
          <span style={{ width: `${progress * 100}%` }} /><em>Uploading {Math.round(progress * 100)}%</em><button onClick={() => ctl.current?.abort()}>Cancel</button>
        </div>
      )}
      {panel === 'emoji' && <div className={c.picker} role="group" aria-label="Emoji">{EMOJI.map((e) => <button key={e} onClick={() => setText((t) => (t + e).slice(0, 1000))} aria-label={e}>{e}</button>)}</div>}
      {panel === 'gif' && <GifPicker base={base} onClose={() => setPanel('')} onPick={(g) => void guard(() => api(`${base}/gifs`, { method: 'POST', body: { url: g.url, title: g.title, threadId } }))} />}
      {panel === 'poll' && (
        <form className={c.panel} onSubmit={(e) => { e.preventDefault(); void guard(() => api(`${base}/polls`, { method: 'POST', body: { question, options: options.filter((o) => o.trim()) } })).then(() => { setQuestion(''); setOptions(['', '']); }); }}>
          <label>Question<input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={200} /></label>
          {options.map((o, i) => <label key={i}>Option {i + 1}<input value={o} onChange={(e) => setOptions(options.map((x, j) => (j === i ? e.target.value : x)))} maxLength={80} /></label>)}
          <div className={c.actionsRow}>
            {options.length < 6 && <Button size="sm" variant="ghost" type="button" icon="plus" onClick={() => setOptions([...options, ''])}>Add option</Button>}
            <Button size="sm" variant="brand" type="submit" loading={busy} disabled={!question.trim() || options.filter((o) => o.trim()).length < 2}>Post poll</Button>
          </div>
        </form>
      )}
      <div className={c.bar2}>
        <textarea value={text} rows={1} maxLength={1000} placeholder={isTeacher ? 'Message the class' : 'Write something kind…'} aria-label="Message"
          onChange={(e) => { setText(e.target.value); onTyping?.(); }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(); } }} />
        <Button variant="brand" icon="send" loading={busy} disabled={!text.trim()} onClick={() => void send()} aria-label="Send" />
      </div>
      <div className={c.tools}>
        <button onClick={() => setPanel(panel === 'emoji' ? '' : 'emoji')} aria-label="Emoji" aria-expanded={panel === 'emoji'}><Icon name="smile" size={20} /></button>
        <button onClick={() => setPanel(panel === 'gif' ? '' : 'gif')} aria-label="GIF" aria-expanded={panel === 'gif'}><b>GIF</b></button>
        <button onClick={() => fileRef.current?.click()} aria-label="Attach a picture or PDF" disabled={progress !== null}><Icon name="paperclip" size={20} /></button>
        <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={(e) => void pickFile(e.target.files?.[0])} />
        {isTeacher && !threadId && <button onClick={() => setPanel(panel === 'poll' ? '' : 'poll')} aria-label="Start a poll" aria-expanded={panel === 'poll'}><Icon name="chart" size={20} /></button>}
        {isTeacher && !threadId && <label className={c.check}><input type="checkbox" checked={announce} onChange={(e) => setAnnounce(e.target.checked)} /> Announcement</label>}
        <span className={c.count}>{text.length}/1000</span>
      </div>
      <p className={c.rules}>No links, phone numbers or emails. Pictures and PDFs up to 4 MB.</p>
    </div>
  );
}
