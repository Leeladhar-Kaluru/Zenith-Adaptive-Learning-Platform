import { Suspense, lazy, useEffect, useRef, useState } from 'react';
import type { Block } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button } from '../ui/kit';
import { Question } from './Question';
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

const LineGraphSim = lazy(() => import('./sims/LineGraphSim').then((m) => ({ default: m.LineGraphSim })));
const EquationSim = lazy(() => import('./sims/EquationSim').then((m) => ({ default: m.EquationSim })));
const DensitySim = lazy(() => import('./sims/DensitySim').then((m) => ({ default: m.DensitySim })));
const SpinnerSim = lazy(() => import('./sims/SpinnerSim').then((m) => ({ default: m.SpinnerSim })));

function Sim({ b }: { b: Extract<Block, { kind: 'widget' }> }) {
  const n = (k: string) => (b.config[k] === undefined ? undefined : Number(b.config[k]));
  const task = b.task ?? '';
  if (b.widget === 'sim_linegraph') return <LineGraphSim blockId={b.id} m0={n('m0')} c0={n('c0')} goal_m={n('goal_m')} goal_c={n('goal_c')} task={task} />;
  if (b.widget === 'sim_equation') return <EquationSim blockId={b.id} a={n('a')} b={n('b')} c={n('c')} task={task} />;
  if (b.widget === 'sim_density') return <DensitySim blockId={b.id} mass0={n('mass0')} vol0={n('vol0')} goal={b.config.goal === undefined ? undefined : String(b.config.goal)} task={task} />;
  return <SpinnerSim blockId={b.id} parts={n('parts')} hit={n('hit')} task={task} />;
}

const CALLOUT = { watch: ['Watch out', 'warn'], remember: ['Remember', 'bookmark'], real: ['In real life', 'globe'] } as const;

export function RenderBlock({ b }: { b: Block }) {
  switch (b.kind) {
    case 'text': return <div className={s.text}>{b.heading && <h2 id={b.id}>{b.heading}</h2>}<Html html={b.html} /></div>;
    case 'figure': return <figure className={s.figure} role="img" aria-label={b.alt}><div dangerouslySetInnerHTML={{ __html: b.svg }} />{b.caption && <figcaption>{b.caption}</figcaption>}</figure>;
    case 'widget': if (b.widget.startsWith('sim_')) return <Suspense fallback={<div className={s.widget}>Loading the simulation…</div>}><Sim b={b} /></Suspense>;
      return b.widget === 'numberline' ? <NumberLine start={Number(b.config.start ?? 0)} min={Number(b.config.min ?? -6)} max={Number(b.config.max ?? 6)} />
      : b.widget === 'balance' ? <Balance a={Number(b.config.a ?? 3)} b={Number(b.config.b ?? 7)} /> : <Fraction num={Number(b.config.num ?? 1)} den={Number(b.config.den ?? 4)} />;
    case 'example': return <Example b={b} />;
    case 'callout': { const [label, icon] = CALLOUT[b.tone]; return <div className={`${s.callout} ${b.tone === 'remember' ? s.remember : b.tone === 'real' ? s.real : ''}`}><span className={s.tagc}><Icon name={icon} size={16} />{label}</span><Html html={b.html} /></div>; }
    case 'check': return <div><h2 id={b.id}>Think first, then check</h2><Question item={b.item} /></div>;
    case 'summary': return <div><h2 id={b.id}>Remember</h2><ul className={s.summary}>{b.points.map((p, i) => <li key={i}><Icon name="check" size={20} accent="var(--ok)" />{p}</li>)}</ul></div>;
  }
}
