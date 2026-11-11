import { useEffect, useRef, useState } from 'react';
import { track } from '../track/tracker';
import { api, ApiError } from '../api/client';
import { clearApiCache, emitProgress } from '../api/useApi';
import type { EvidenceResult, PublicItem, Response } from '../api/types';
import { useFx } from '../fx/fx';
import { Icon } from '../icons/Icon';
import { queueEvidence } from '../offline/sync';
import { Button, useToast } from '../ui/kit';
import s from './lesson.module.css';

interface Props {
  item: PublicItem;
  context?: 'learn_check' | 'solve' | 'test' | 'probe';
  sessionId?: string;
  /** Tests: record the answer but do not reveal whether it was right until the test is submitted. */
  deferFeedback?: boolean;
  onResult?: (r: EvidenceResult | null) => void;
  resetKey?: string | number;
}

const prettyBadge = (c: string) => c.replace(/_/g, ' ').replace(/^./, (x) => x.toUpperCase());

function reveal(item: PublicItem, r: unknown): string {
  if (item.kind === 'mcq') return item.options?.find((o) => o.key === r)?.text ?? String(r);
  if (item.kind === 'multi') return (r as string[]).map((k) => item.options?.find((o) => o.key === k)?.text ?? k).join(', ');
  if (item.kind === 'truefalse') return r ? 'True' : 'False';
  if (item.kind === 'find_error') return `Line ${Number(r) + 1}`;
  if (item.kind === 'match' || item.kind === 'label_diagram') return Object.entries(r as Record<string, string>).map(([a, b]) => `${a} → ${b}`).join('; ');
  return String(r);
}

export function Question({ item, context = 'learn_check', sessionId, deferFeedback, onResult, resetKey }: Props) {
  const [choice, setChoice] = useState<string | null>(null);
  const [multi, setMulti] = useState<string[]>([]);
  const [step, setStep] = useState<number | null>(null);
  const [tf, setTf] = useState<boolean | null>(null);
  const [text, setText] = useState('');
  const [pairs, setPairs] = useState<Record<string, string>>({});
  const [hints, setHints] = useState<string[]>([]);
  const [res, setRes] = useState<EvidenceResult | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const t0 = useRef(Date.now());
  const fx = useFx();
  const toast = useToast();

  useEffect(() => {
    setChoice(null); setStep(null); setMulti([]); setTf(null); setText(''); setPairs({}); setHints([]); setRes(null); setSaved(false); t0.current = Date.now(); picked.current = false;
  }, [item.id, resetKey]);

  // Changing a picked answer (not the first pick) is a signal the student was unsure.
  const picked = useRef(false);
  const sig = JSON.stringify([choice, multi, tf, pairs, step]);
  useEffect(() => {
    if (item.kind === 'numeric' || item.kind === 'fill' || res || saved) return;
    if (choice === null && !multi.length && tf === null && step === null && !Object.keys(pairs).length) return;
    if (picked.current) track('answer_change', 'item', item.id, {}, Date.now() - t0.current);
    picked.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig]);

  const response = (): Response | null => {
    switch (item.kind) {
      case 'mcq': return choice ? { choice } : null;
      case 'multi': return multi.length ? { choices: multi } : null;
      case 'find_error': return step === null ? null : { step };
      case 'truefalse': return tf === null ? null : { choice: tf };
      case 'numeric': return text.trim() ? { value: text.trim() } : null;
      case 'fill': return text.trim() ? { text: text.trim() } : null;
      case 'match': return item.left && item.left.every((l) => pairs[l]) ? { pairs } : null;
      case 'label_diagram': return item.regions && item.regions.every((r) => pairs[r]) ? { pairs } : null;
    }
  };

  async function submit() {
    const r = response();
    if (!r || busy) return;
    setBusy(true);
    const req = { itemId: item.id, response: r, hintsUsed: hints.length, ms: Date.now() - t0.current, context, clientEventId: crypto.randomUUID(), sessionId };
    try {
      const out = await api<EvidenceResult>('/evidence', { method: 'POST', body: req });
      clearApiCache();
      if (deferFeedback) { setSaved(true); onResult?.(null); return; }
      setRes(out);
      emitProgress();
      if (out.correct && out.xp > 0) fx.xp(out.xp);
      const up = out.changes.find((c) => c.to === 'secure');
      if (up) toast(`${up.title} is now secure`, 'ok');
      if (out.levelChange) toast(`Level ${out.levelChange.from} to ${out.levelChange.to}. ${out.levelChange.reason}`, 'ok');
      if (out.newBadges.length) fx.celebrate({ title: 'New badge', text: out.newBadges.map(prettyBadge).join(', '), icon: 'medal' });
      onResult?.(out);
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        await queueEvidence(req);
        setSaved(true);
        toast('Saved on this device. ZENITH will check it when you are back online.', 'info');
        onResult?.(null);
      } else toast((e as Error).message, 'err');
    } finally { setBusy(false); }
  }

  async function hint() {
    try {
      const h = await api<{ hint: string }>(`/items/${item.id}/hint?n=${hints.length + 1}`);
      setHints((x) => [...x, h.hint]);
      track('hint_open', 'item', item.id, { n: hints.length + 1 }, Date.now() - t0.current);
    } catch (e) { toast((e as Error).message, 'err'); }
  }

  const done = !!res || saved;
  const optState = (key: string) => (res && item.kind === 'mcq' ? (key === res.reveal ? s.ok : key === choice ? s.retry : '') : '');

  return (
    <div>
      <p style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 4 }}>{item.stem}</p>

      {item.kind === 'mcq' && (
        <div className={s.opts} role="radiogroup" aria-label="Choose one answer">
          {item.options?.map((o) => (
            <button key={o.key} className={`${s.opt} ${optState(o.key)}`} role="radio" aria-checked={choice === o.key} disabled={done} onClick={() => setChoice(o.key)}>
              <b>{o.key}</b>{o.text}{res && o.key === res.reveal && <Icon name="check" size={22} />}
            </button>
          ))}
        </div>
      )}
      {item.kind === 'find_error' && (
        <ol className={s.opts} role="radiogroup" aria-label="Which line is wrong?" style={{ listStyle: 'none', padding: 0 }}>
          {item.steps?.map((line, i) => {
            const right = res && i === Number(res.reveal);
            const state = res ? (right ? s.ok : i === step ? s.retry : '') : '';
            return (
              <li key={i}><button className={`${s.opt} ${state}`} role="radio" aria-checked={step === i} disabled={done || i === 0} onClick={() => setStep(i)}>
                <b>{i + 1}</b>{line}{right && <Icon name="check" size={22} />}
              </button></li>
            );
          })}
        </ol>
      )}
      {item.kind === 'multi' && (
        <div className={s.opts} role="group" aria-label="Choose all that apply">
          {item.options?.map((o) => {
            const on = multi.includes(o.key);
            return <button key={o.key} className={s.opt} role="checkbox" aria-checked={on} disabled={done} onClick={() => setMulti(on ? multi.filter((k) => k !== o.key) : [...multi, o.key])}><b>{on ? <Icon name="check" size={16} /> : o.key}</b>{o.text}</button>;
          })}
        </div>
      )}
      {item.kind === 'truefalse' && (
        <div className={s.opts} role="radiogroup" aria-label="True or false">
          {[true, false].map((v) => (
            <button key={String(v)} className={`${s.opt} ${res ? (v === res.reveal ? s.ok : v === tf ? s.retry : '') : ''}`} role="radio" aria-checked={tf === v} disabled={done} onClick={() => setTf(v)}><b>{v ? 'T' : 'F'}</b>{v ? 'True' : 'False'}</button>
          ))}
        </div>
      )}
      {(item.kind === 'numeric' || item.kind === 'fill') && (
        <div style={{ margin: '14px 0', display: 'flex', gap: 10, alignItems: 'center' }}>
          <input className={s.answer} value={text} onChange={(e) => setText(e.target.value)} disabled={done} inputMode={item.kind === 'numeric' ? 'decimal' : 'text'} autoComplete="off"
            aria-label="Your answer" placeholder={item.kind === 'numeric' ? 'Type a number' : 'Type your answer'} onKeyDown={(e) => e.key === 'Enter' && void submit()} />
          {item.unit && <span className="muted" style={{ fontWeight: 700 }}>{item.unit}</span>}
        </div>
      )}
      {item.kind === 'label_diagram' && (
        <div>
          <div className={s.figure} role="img" aria-label={`Diagram with ${item.regions?.length ?? 0} numbered parts`} dangerouslySetInnerHTML={{ __html: item.svg ?? '' }} />
          <div className={s.opts}>
            {item.regions?.map((r) => (
              <label key={r} className={s.matchRow}><span style={{ fontWeight: 700 }}>Part {r}</span>
                <select className={s.answer} value={pairs[r] ?? ''} disabled={done} onChange={(e) => setPairs({ ...pairs, [r]: e.target.value })} aria-label={`Name for part ${r}`}>
                  <option value="">Choose…</option>{item.labels?.map((l) => <option key={l} value={l}>{l}</option>)}
                </select></label>
            ))}
          </div>
        </div>
      )}
      {item.kind === 'match' && (
        <div className={s.opts}>
          {item.left?.map((l) => (
            <label key={l} className={s.matchRow}><span style={{ fontWeight: 700 }}>{l}</span>
              <select className={s.answer} value={pairs[l] ?? ''} disabled={done} onChange={(e) => setPairs({ ...pairs, [l]: e.target.value })} aria-label={`Match for ${l}`}>
                <option value="">Choose…</option>{item.right?.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
          ))}
        </div>
      )}

      {hints.map((h, i) => !res && <div key={i} className={`${s.fb} ${s.fbHint}`}><Icon name="bulb" size={18} /> Hint {i + 1}: {h}</div>)}
      {res && (
        <div className={`${s.fb} ${res.correct ? s.fbOk : s.fbRetry}`} role="status">
          <strong>{res.correct ? 'Correct. ' : `Not quite. The answer is ${reveal(item, res.reveal)}. `}</strong>{res.feedback}
          {res.concepts[0] && <div className="sm" style={{ marginTop: 6, opacity: .85 }}>{res.concepts[0].title}: {res.concepts[0].evidence} answer{res.concepts[0].evidence === 1 ? '' : 's'} so far, confidence {res.concepts[0].confidence}.</div>}
        </div>
      )}
      {saved && !res && <div className={`${s.fb} ${s.fbOk}`} role="status">{deferFeedback ? 'Answer saved.' : 'Saved on this device. It will be checked when you are online.'}</div>}

      {!done && (
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Button variant="brand" onClick={() => void submit()} loading={busy} disabled={!response()}>{deferFeedback ? 'Save answer' : 'Check my answer'}</Button>
          {!deferFeedback && item.hintCount > hints.length && <Button variant="ghost" icon="bulb" onClick={() => void hint()}>Hint ({hints.length}/{item.hintCount})</Button>}
        </div>
      )}
    </div>
  );
}
