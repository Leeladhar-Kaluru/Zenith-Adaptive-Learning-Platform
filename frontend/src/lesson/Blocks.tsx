import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { Block, EvidenceResult, PublicItem } from '../api/types';
import { useFx } from '../fx/fx';
import { Icon } from '../icons/Icon';
import { Button, useToast } from '../ui/kit';
import { Balance, Fraction, NumberLine } from './widgets';
import s from './lesson.module.css';

/** Content HTML comes only from reviewed, server-sanitised lessons. Maths is `<span data-tex="...">`. */
function Html({ html, className }: { html: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const nodes = ref.current?.querySelectorAll<HTMLElement>('[data-tex]');
    if (!nodes || nodes.length === 0) return;
    let live = true;
    void Promise.all([import('katex'), import('katex/dist/katex.min.css')]).then(([k]) => {
      if (!live) return;
      nodes.forEach((n) => k.default.render(n.dataset.tex ?? '', n, { throwOnError: false, displayMode: n.dataset.display === '1' }));
    });
    return () => { live = false; };
  }, [html]);
  return <div ref={ref} className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

export function Check({ item, context = 'learn_check', onResult, resetKey }: {
  item: PublicItem; context?: 'learn_check' | 'solve' | 'test' | 'probe'; onResult?: (r: EvidenceResult) => void; resetKey?: string | number;
}) {
  const [sel, setSel] = useState<string | null>(null);
  const [res, setRes] = useState<EvidenceResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [hints, setHints] = useState(0);
  const t0 = useRef(Date.now());
  const fx = useFx();
  const toast = useToast();
  useEffect(() => { setSel(null); setRes(null); setHints(0); t0.current = Date.now(); }, [item.id, resetKey]);

  async function check() {
    if (!sel || busy) return;
    setBusy(true);
    try {
      const r = await api<EvidenceResult>('/evidence', { method: 'POST', body: { itemId: item.id, choice: sel, hintsUsed: hints, ms: Date.now() - t0.current, context, clientEventId: crypto.randomUUID() } });
      setRes(r);
      if (r.correct) fx.xp(r.xp);
      onResult?.(r);
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }
  const retry = () => { setRes(null); setSel(null); t0.current = Date.now(); };

  return (
    <div>
      <p style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 4 }}>{item.stem}</p>
      <div className={s.opts} role="radiogroup" aria-label="Choose an answer">
        {item.options.map((o) => {
          const state = res ? (o.key === res.correctKey ? s.ok : o.key === sel ? s.retry : '') : '';
          return (
            <button key={o.key} className={`${s.opt} ${state}`} role="radio" aria-checked={sel === o.key} disabled={!!res} onClick={() => setSel(o.key)}>
              <b>{o.key}</b>{o.text}
              {res && o.key === res.correctKey && <Icon name="check" size={22} />}
            </button>
          );
        })}
      </div>
      {res && <div className={`${s.fb} ${res.correct ? s.fbOk : s.fbRetry}`} role="status">{res.feedback}</div>}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {!res && <Button variant="brand" onClick={check} loading={busy} disabled={!sel}>Check my answer</Button>}
        {!res && item.hintCount > hints && <Button variant="ghost" icon="bulb" onClick={() => setHints((h) => h + 1)}>Hint {hints > 0 ? `(${hints}/${item.hintCount})` : ''}</Button>}
        {res && !res.correct && <Button variant="ghost" icon="refresh" onClick={retry}>Try again</Button>}
      </div>
      {hints > 0 && !res && <div className={`${s.fb} ${s.fbRetry}`} style={{ marginTop: 10 }}>Hint {hints}: look at the number line above and think about which direction you move.</div>}
    </div>
  );
}

function Example({ b }: { b: Extract<Block, { kind: 'example' }> }) {
  const [n, setN] = useState(1);
  return (
    <div>
      <h2>{b.heading}</h2>
      <p className={s.text}>{b.prompt}</p>
      <ol className={s.steps}>{b.steps.slice(0, n).map((st, i) => <li key={i}><span>{st}</span></li>)}</ol>
      {n < b.steps.length ? <Button variant="ghost" size="sm" iconRight="arrowR" onClick={() => setN(n + 1)}>Show next step</Button> : <p className="hand">that is the whole idea. now you try</p>}
    </div>
  );
}

const CALLOUT = { watch: ['Watch out', 'warn'], remember: ['Remember', 'bookmark'], real: ['In real life', 'globe'] } as const;

export function RenderBlock({ b }: { b: Block }) {
  switch (b.kind) {
    case 'text': return <div className={s.text}>{b.heading && <h2 id={b.id}>{b.heading}</h2>}<Html html={b.html} /></div>;
    case 'figure': return <figure className={s.figure} role="img" aria-label={b.alt}><div dangerouslySetInnerHTML={{ __html: b.svg }} />{b.caption && <figcaption>{b.caption}</figcaption>}</figure>;
    case 'widget': return b.widget === 'numberline' ? <NumberLine start={Number(b.config.start ?? 0)} min={Number(b.config.min ?? -6)} max={Number(b.config.max ?? 6)} />
      : b.widget === 'balance' ? <Balance a={Number(b.config.a ?? 3)} b={Number(b.config.b ?? 7)} /> : <Fraction num={Number(b.config.num ?? 1)} den={Number(b.config.den ?? 4)} />;
    case 'example': return <Example b={b} />;
    case 'callout': { const [label, icon] = CALLOUT[b.tone]; return <div className={`${s.callout} ${b.tone === 'remember' ? s.remember : b.tone === 'real' ? s.real : ''}`}><span className={s.tagc}><Icon name={icon} size={16} />{label}</span><Html html={b.html} /></div>; }
    case 'check': return <div><h2 id={b.id}>Think first, then check</h2><Check item={b.item} /></div>;
    case 'summary': return <div><h2 id={b.id}>Remember</h2><ul className={s.summary}>{b.points.map((p, i) => <li key={i}><Icon name="check" size={20} accent="var(--ok)" />{p}</li>)}</ul></div>;
  }
}
