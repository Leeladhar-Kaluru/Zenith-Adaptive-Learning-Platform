import { useState } from 'react';
import { SimFrame, useSimId, clamp } from './SimFrame';
import { track } from '../../track/tracker';
import s from './sims.module.css';

/* Exact fractions so that dividing never produces a rounding surprise. */
type F = [number, number];
const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : Math.abs(a));
const norm = ([n, d]: F): F => { const g = gcd(n, d) || 1; const sg = d < 0 ? -1 : 1; return [(sg * n) / g, (sg * d) / g]; };
const add = (a: F, b: F): F => norm([a[0] * b[1] + b[0] * a[1], a[1] * b[1]]);
const mul = (a: F, b: F): F => norm([a[0] * b[0], a[1] * b[1]]);
const show = ([n, d]: F) => { const t = d === 1 ? String(Math.abs(n)) : `${Math.abs(n)}/${d}`; return n < 0 ? `−${t}` : t; };

interface Eq { p: F; q: F; r: F }          // p x + q = r
const side = (p: F, q: F) => {
  const px = p[0] === 0 ? '' : p[0] === p[1] ? 'x' : p[0] === -p[1] ? '−x' : `${show(p)}x`;
  if (q[0] === 0) return px || '0';
  return px ? `${px} ${q[0] < 0 ? '−' : '+'} ${show([Math.abs(q[0]), q[1]])}` : show(q);
};
const text = (e: Eq) => `${side(e.p, e.q)} = ${show(e.r)}`;
const isSolved = (e: Eq) => e.p[0] === e.p[1] && e.q[0] === 0;

/** Solve p x + q = r by choosing an operation and a number, applied to both sides. Every choice is visible and reversible. */
export function EquationSim({ blockId, a = 2, b = 3, c = 11, task = '' }: { blockId: string; a?: number; b?: number; c?: number; task?: string }) {
  const simId = useSimId(blockId);
  const start = (): Eq => ({ p: [clamp(a, 1, 12), 1], q: [clamp(b, -20, 20), 1], r: [clamp(c, -60, 60), 1] });
  const [eq, setEq] = useState<Eq>(start);
  const [log, setLog] = useState<string[]>([]);
  const [n, setN] = useState(3);
  const [note, setNote] = useState('');
  const done = isSolved(eq);

  function apply(op: '+' | '−' | '×' | '÷') {
    if (done) return;
    if (op === '÷' && n === 0) { setNote('You cannot divide by zero.'); return; }
    const k: F = [n, 1];
    let next: Eq;
    if (op === '+') next = { p: eq.p, q: add(eq.q, k), r: add(eq.r, k) };
    else if (op === '−') next = { p: eq.p, q: add(eq.q, [-n, 1]), r: add(eq.r, [-n, 1]) };
    else if (op === '×') next = { p: mul(eq.p, k), q: mul(eq.q, k), r: mul(eq.r, k) };
    else { const inv: F = [1, n]; next = { p: mul(eq.p, inv), q: mul(eq.q, inv), r: mul(eq.r, inv) }; }
    const big = [next.p, next.q, next.r].some(([x, y]) => Math.abs(x) > 5000 || y > 5000);
    if (big) { setNote('That makes the numbers huge. Try a smaller step.'); return; }
    // A useful operation removes the constant or the coefficient; tell the student honestly which kind it was.
    const helped = (eq.q[0] !== 0 && next.q[0] === 0) || (next.p[0] === next.p[1] && eq.p[0] !== eq.p[1]);
    setNote(helped ? 'Good move: that simplified the equation.' : 'That kept the equation balanced, but did not get x alone. Look at what is stuck to x.');
    setEq(next);
    setLog((l) => [...l, `${op} ${n} on both sides: ${text(next)}`]);
    track('sim_change', 'sim', simId, { op, n, helped });
  }

  return (
    <SimFrame title="Keep the balance" task={task || 'Get x on its own.'} simId={simId} done={done}
      onReset={() => { setEq(start()); setLog([]); setNote(''); }}
      controls={<>
        <label className={s.slider}><span>Number: <b>{n}</b></span>
          <input type="range" min={1} max={12} value={n} aria-valuetext={String(n)} onChange={(e) => setN(clamp(Number(e.target.value), 1, 12))} /></label>
        <div className={s.ops} role="group" aria-label="Do this to both sides">
          {(['+', '−', '×', '÷'] as const).map((op) => <button key={op} type="button" className={s.op} disabled={done} onClick={() => apply(op)} aria-label={`${op === '+' ? 'Add' : op === '−' ? 'Subtract' : op === '×' ? 'Multiply by' : 'Divide by'} ${n} on both sides`}>{op} {n}</button>)}
        </div></>}
      readout={done ? `x = ${show(eq.r)}` : text(eq)}>
      <div className={s.balance} aria-hidden="true"><span className={s.pan}>{side(eq.p, eq.q)}</span><span className={s.beam} /><span className={s.pan}>{show(eq.r)}</span></div>
      <p className={s.note} role="status">{note || 'Whatever you do to one side, do to the other.'}</p>
      {log.length > 0 && <ol className={s.log}>{log.slice(-4).map((l, i) => <li key={i}>{l}</li>)}</ol>}
    </SimFrame>
  );
}
