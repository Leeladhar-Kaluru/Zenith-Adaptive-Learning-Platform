import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { TutorReply } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { Avatar, Icon } from '../icons/Icon';
import { db } from '../offline/db';
import { DOUBTS_EVENT, queueDoubt } from '../offline/sync';
import { Button, Chip } from '../ui/kit';
import s from './ask.module.css';

interface Msg { who: 'me' | 'ai'; text: string; reply?: TutorReply; error?: boolean; waiting?: boolean }
const LANGS = [{ v: 'en', l: 'English' }, { v: 'hi', l: 'हिन्दी' }, { v: 'te', l: 'తెలుగు' }] as const;
const PROMPTS = ['Explain it in a simpler way', 'Give me another example', 'Why is this true?', 'What mistake should I avoid?'];

export default function AskPanel({ lessonId, compact }: { lessonId?: string; compact?: boolean }) {
  const { profile } = useAuth();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [lang, setLang] = useState<'en' | 'hi' | 'te'>(profile?.language ?? 'en');
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const [waiting, setWaiting] = useState<string[]>([]);
  // Questions asked offline: answered or failed ones join the chat (once), queued ones show as waiting.
  useEffect(() => {
    const load = async () => {
      try {
        const mine = (await db.doubts.toArray()).filter((d) => (d.lessonId ?? undefined) === lessonId).sort((a, b) => a.askedAt.localeCompare(b.askedAt));
        setWaiting(mine.filter((d) => d.status === 'queued').map((d) => d.message));
        const ready = mine.filter((d) => d.status !== 'queued');
        if (!ready.length) return;
        await db.doubts.bulkDelete(ready.map((d) => d.clientId));
        setMsgs((m) => [...m, ...ready.flatMap<Msg>((d) => [{ who: 'me', text: d.message }, d.reply ? { who: 'ai', text: d.reply.reply, reply: d.reply } : { who: 'ai', text: d.error ?? 'ZENITH could not answer.', error: true }])]);
      } catch { /* no local storage: online questions still work */ }
    };
    void load();
    addEventListener(DOUBTS_EVENT, load);
    return () => removeEventListener(DOUBTS_EVENT, load);
  }, [lessonId]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [msgs, busy]);

  async function saveForLater(message: string) {
    try { await queueDoubt(message, lang, lessonId); setMsgs((m) => m.slice(0, -1)); } catch { setMsgs((m) => [...m, { who: 'ai', text: 'You are offline and this device could not save your question. Try again when you are online.', error: true }]); }
  }
  async function send(q: string) {
    const message = q.trim();
    if (!message || busy) return;
    setMsgs((m) => [...m, { who: 'me', text: message }]);
    setText('');
    setBusy(true);
    if (!navigator.onLine) { await saveForLater(message); setBusy(false); return; }
    try {
      const reply = await api<TutorReply>('/tutor/ask', { method: 'POST', body: { message, lessonId, language: lang } });
      setMsgs((m) => [...m, { who: 'ai', text: reply.reply, reply }]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) { await saveForLater(message); return; }
      const msg = e instanceof ApiError && e.status === 429 ? 'You have asked a lot today. Try again tomorrow, or reread the lesson.' : 'ZENITH could not answer right now. Your question is not lost; try again in a moment.';
      setMsgs((m) => [...m, { who: 'ai', text: msg, error: true }]);
    } finally { setBusy(false); }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void send(text); };

  return (
    <div className={`${s.panel} ${compact ? s.compact : ''}`}>
      <div className={s.head}>
        <div className={s.row}><Icon name="chat" size={22} /><strong>Ask ZENITH</strong></div>
        <div className={s.langs} role="group" aria-label="Reply language">
          {LANGS.map((l) => <button key={l.v} aria-pressed={lang === l.v} onClick={() => setLang(l.v)} lang={l.v}>{l.l}</button>)}
        </div>
      </div>
      <div className={s.log} role="log" aria-live="polite">
        {msgs.length === 0 && (
          <div className={s.hello}>
            <p className="hand" style={{ fontSize: '1.3rem' }}>Stuck? Ask me anything about this lesson.</p>
            <p className="sm muted">I will guide you with questions instead of just giving the answer.</p>
            <div className={s.chips}>{PROMPTS.map((p) => <button key={p} className={s.sugg} onClick={() => void send(p)}>{p}</button>)}</div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`${s.msg} ${m.who === 'me' ? s.me : s.ai} ${m.error ? s.errMsg : ''}`}>
            {m.who === 'me' ? <Avatar id={profile?.avatar} size={30} /> : <span className={s.bot}><Icon name="spark" size={18} /></span>}
            <div>
              <p>{m.text}</p>
              {m.reply?.aiTranslated && <Chip icon="globe" tone="soft">AI-translated, not reviewed</Chip>}
              {m.reply?.degraded && <Chip icon="warn" tone="soft">Answered from the lesson only</Chip>}
              {m.reply && m.reply.citations.length > 0 && <p className="sm muted" style={{ marginTop: 6 }}>From: {m.reply.citations.map((c) => `${c.title} · ${c.heading}`).join('; ')}</p>}
            </div>
          </div>
        ))}
        {busy && <div className={`${s.msg} ${s.ai}`}><span className={s.bot}><Icon name="spark" size={18} /></span><span className={s.typing} aria-label="ZENITH is thinking"><i /><i /><i /></span></div>}
        {waiting.map((w, i) => <div key={`w${i}`} className={`${s.msg} ${s.me}`}><Avatar id={profile?.avatar} size={30} /><div><p>{w}</p><p className="sm muted"><Icon name="wifiOff" size={14} /> Saved on this device. ZENITH will answer when you are back online.</p></div></div>)}
        <div ref={end} />
      </div>
      <form className={s.form} onSubmit={submit}>
        <input className={s.input} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your question" maxLength={500} aria-label="Your question" />
        <Button type="submit" variant="brand" icon="send" disabled={!text.trim() || busy} aria-label="Send" />
      </form>
      <p className="sm muted" style={{ textAlign: 'center' }}>ZENITH is an AI helper and can make mistakes. Check with your teacher.</p>
    </div>
  );
}
