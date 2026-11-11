import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import type { PublicItem } from '../api/types';
import { useClassRealtime } from '../chat/realtime';
import { Avatar } from '../icons/Icon';
import { Button, Card, EmptyState } from '../ui/kit';
import { pw } from '../ui/powers';
import c from './classes.module.css';

interface Opp { nickname: string; avatar: string | null; answered: number; score: number; finished: boolean }
interface Review { stem: string; correct: boolean | null; explanation: string }
interface Result { youWon: boolean; draw: boolean; ratingBefore: number; ratingAfter: number; forfeit: boolean; review: Review[] }
interface Match {
  id: string; status: 'waiting' | 'active' | 'done' | 'cancelled'; total: number; myScore: number; myAnswered: number; opponent?: Opp;
  deadlineAt?: string; question?: PublicItem & { position: number }; result?: Result;
}
interface Standings { table: Array<{ nickname: string; avatar: string; rating: number; games: number; you: boolean }>; mine: number | null }

/** 1v1 quiz against a classmate. The server picks the questions, times the answers and grades them; this page only shows state it asks for every 1.5 seconds. */
export function ClassQuiz({ classId, avatar, nickname = '', resumeId, onDone }: { classId: string; avatar?: string; nickname?: string; resumeId?: string | null; onDone?: () => void }) {
  const [m, setM] = useState<Match | null>(null);
  const [table, setTable] = useState<Standings | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState('');
  const [flash, setFlash] = useState<{ correct: boolean; points: number } | null>(null);
  const [now, setNow] = useState(Date.now());
  const sending = useRef(false);
  const matchId = useRef<string | null>(null);
  matchId.current = m?.id ?? null;
  const refresh = useCallback(() => { const id = matchId.current; if (id && !sending.current) void api<Match>(`/quiz/${id}`).then((s) => { if (!sending.current) setM(s); }).catch(() => undefined); }, []);
  const live = useClassRealtime(classId, nickname, refresh);          // a content-free ping: "something changed, ask the server"
  useEffect(() => { if (resumeId) void api<Match>(`/quiz/${resumeId}`).then(setM).catch(() => undefined); }, [resumeId]);

  const loadTable = useCallback(() => { void api<Standings>(`/classes/${classId}/quiz/standings`).then(setTable).catch(() => undefined); }, [classId]);
  useEffect(loadTable, [loadTable]);

  const running = m?.status === 'waiting' || m?.status === 'active';
  useEffect(() => {
    if (!running || !m) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    const poll = setInterval(refresh, live.connected ? 5000 : 1500);      // Realtime does the fast work when connected; polling is the safety net
    return () => { clearInterval(tick); clearInterval(poll); };
  }, [running, m?.id, live.connected, refresh]);
  useEffect(() => { if (m?.status === 'done') { loadTable(); onDone?.(); } }, [m?.status, loadTable]); // eslint-disable-line react-hooks/exhaustive-deps

  const call = async <T,>(path: string, body?: unknown): Promise<T | null> => {
    setErr('');
    try { return await api<T>(path, { method: 'POST', body }); } catch (e) { setErr(e instanceof ApiError ? e.message : 'Something went wrong. Try again.'); return null; }
  };
  const find = async () => { setBusy(true); const s = await call<Match>(`/classes/${classId}/quiz/join`); setBusy(false); if (s) { setM(s); setFlash(null); live.ping(); } };
  const leave = async () => { if (m) { const s = await call<Match>(`/quiz/${m.id}/leave`); if (s) { setM(s.status === 'cancelled' ? null : s); live.ping(); } } };
  const send = async (response: Record<string, unknown>) => {
    if (!m?.question || sending.current) return;
    sending.current = true; setBusy(true);
    const r = await call<{ correct: boolean; points: number }>(`/quiz/${m.id}/answer`, { position: m.question.position, response });
    if (r) { setFlash(r); setText(''); const s = await api<Match>(`/quiz/${m.id}`).catch(() => null); if (s) setM(s); live.ping(); }
    sending.current = false; setBusy(false);
  };

  const left = m?.deadlineAt ? Math.max(0, Math.round((new Date(m.deadlineAt).getTime() - now) / 1000)) : 0;
  const q = m?.question;

  return (
    <div className={c.list}>
      {(!m || m.status === 'cancelled') && (
        <Card>
          <h3>1v1 quiz</h3>
          <p className="muted">Five questions, same for both of you, matched with a classmate at about your level. Faster correct answers score more. Only your nickname and picture are shown.</p>
          {m?.status === 'cancelled' && <p className="muted">Nobody joined in time. Try again.</p>}
          {err && <p role="alert" style={{ color: 'var(--bad, #c0392b)' }}>{err}</p>}
          <Button variant="brand" icon="spark" loading={busy} onClick={() => void find()}>Find an opponent</Button>
          {table?.mine != null && <p className="sm muted" style={{ marginTop: 10 }}>Your quiz rating: <b>{table.mine}</b></p>}
        </Card>
      )}

      {m?.status === 'waiting' && (
        <Card><h3>Looking for a classmate…</h3><p className="muted">Stay on this page. The match starts as soon as someone from your class joins.</p>
          <Button variant="ghost" onClick={() => void leave()}>Cancel</Button></Card>
      )}

      {m?.status === 'active' && (
        <Card>
          <div className={c.noteHead}>
            <span className={c.mate}><Avatar id={avatar} size={28} /><span>You · {m.myScore}</span></span>
            <span className="sm muted" aria-live="off">{Math.floor(left / 60)}:{String(left % 60).padStart(2, '0')} left</span>
            {m.opponent && <span className={c.mate}><Avatar id={m.opponent.avatar ?? undefined} size={28} /><span>{m.opponent.nickname} · {m.opponent.answered}/{m.total}{m.opponent.finished ? ' ✓' : ''}</span></span>}
          </div>
          {q ? (
            <div style={{ marginTop: 14 }}>
              <p className="sm muted">Question {q.position + 1} of {m.total}</p>
              <p style={{ fontWeight: 700 }}>{pw(q.stem)}</p>
              {flash && <p role="status" className="sm" style={{ color: flash.correct ? 'var(--ok)' : 'var(--ink-2)' }}>{flash.correct ? `Correct! +${flash.points}` : 'Not this time.'}</p>}
              {(q.kind === 'mcq' || q.kind === 'truefalse') && (
                <div className={c.actions} role="group" aria-label="Answers">
                  {q.kind === 'mcq' ? q.options?.map((o) => <Button key={o.key} variant="primary" disabled={busy} onClick={() => void send({ choice: o.key })}>{pw(o.text)}</Button>)
                    : [true, false].map((v) => <Button key={String(v)} variant="primary" disabled={busy} onClick={() => void send({ choice: v })}>{v ? 'True' : 'False'}</Button>)}
                </div>
              )}
              {q.kind === 'numeric' && (
                <form className={c.join} onSubmit={(e) => { e.preventDefault(); if (text.trim()) void send({ value: text.trim() }); }}>
                  <input className={c.input} inputMode="decimal" value={text} onChange={(e) => setText(e.target.value)} aria-label={`Your answer${q.unit ? ` in ${q.unit}` : ''}`} placeholder={q.unit ? `Answer (${q.unit})` : 'Answer'} />
                  <Button type="submit" variant="brand" disabled={busy || !text.trim()}>Check</Button>
                </form>
              )}
            </div>
          ) : <p className="muted" style={{ marginTop: 14 }}>You are done. Waiting for {m.opponent?.nickname ?? 'your opponent'} to finish…</p>}
          <div style={{ marginTop: 12 }}><Button size="sm" variant="ghost" onClick={() => void leave()}>Give up</Button></div>
          {err && <p role="alert">{err}</p>}
        </Card>
      )}

      {m?.status === 'done' && m.result && (
        <Card>
          <h3>{m.result.draw ? 'A draw' : m.result.youWon ? 'You won!' : 'Good game'}{m.result.forfeit ? ' (your opponent left)' : ''}</h3>
          <p>Your score: <b>{m.myScore}</b>{m.opponent && <> · {m.opponent.nickname}: <b>{m.opponent.score}</b></>}</p>
          <p className="muted">Quiz rating {m.result.ratingBefore} → <b>{m.result.ratingAfter}</b></p>
          <ol style={{ paddingLeft: 18 }}>{m.result.review.map((r, i) => <li key={i}><span aria-label={r.correct ? 'correct' : 'not correct'}>{r.correct ? '✓' : '✗'}</span> {pw(r.stem)}{r.explanation && <p className="sm muted">{pw(r.explanation)}</p>}</li>)}</ol>
          <Button variant="brand" icon="refresh" onClick={() => { setM(null); setFlash(null); }}>Play again</Button>
        </Card>
      )}

      <Card flat>
        <h3>Quiz table</h3>
        {table && table.table.length > 0 ? (
          <ol className={c.mates} style={{ listStyle: 'none', padding: 0 }}>{table.table.map((r) => <li key={r.nickname} className={c.mate}><Avatar id={r.avatar} size={28} /><span>{r.nickname}{r.you ? ' (you)' : ''} · {r.rating}</span></li>)}</ol>
        ) : <EmptyState icon="trophy" title="No games yet" text="Play a match and your rating shows up here for your class." />}
      </Card>
    </div>
  );
}
