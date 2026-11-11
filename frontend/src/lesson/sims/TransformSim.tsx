import { useState } from 'react';
import { SimFrame, useSimId, clamp } from './SimFrame';
import { applyMoves, samePoints, type Move, type P } from './physics';
import s from './sims.module.css';

const MOVES: Array<{ label: string; move: Move }> = [
  { label: 'Right 1', move: { op: 'move', dx: 1, dy: 0 } }, { label: 'Left 1', move: { op: 'move', dx: -1, dy: 0 } },
  { label: 'Up 1', move: { op: 'move', dx: 0, dy: 1 } }, { label: 'Down 1', move: { op: 'move', dx: 0, dy: -1 } },
  { label: 'Reflect in x-axis', move: { op: 'reflect', axis: 'x' } }, { label: 'Reflect in y-axis', move: { op: 'reflect', axis: 'y' } },
  { label: 'Rotate 90° anticlockwise', move: { op: 'rotate' } },
];
const g = (v: number | undefined, d: number) => Math.round(clamp(v ?? d, -8, 8));
type Corners = { a1?: number; a2?: number; b1?: number; b2?: number; c1?: number; c2?: number; ta1?: number; ta2?: number; tb1?: number; tb2?: number; tc1?: number; tc2?: number };

/** Slide, flip and turn a triangle on a grid until it lands on the target triangle. */
export function TransformSim({ blockId, task = '', ...c }: { blockId: string; task?: string } & Corners) {
  const simId = useSimId(blockId);
  const start: P[] = [[g(c.a1, 1), g(c.a2, 1)], [g(c.b1, 3), g(c.b2, 1)], [g(c.c1, 1), g(c.c2, 3)]];
  const target: P[] | null = c.ta1 === undefined ? null : [[g(c.ta1, 0), g(c.ta2, 0)], [g(c.tb1, 0), g(c.tb2, 0)], [g(c.tc1, 0), g(c.tc2, 0)]];
  const [moves, setMoves] = useState<Move[]>([]);
  const now = applyMoves(start, moves);
  const done = target !== null && samePoints(now, target);
  const X = (x: number) => 150 + x * 16, Y = (y: number) => 130 - y * 16;
  const poly = (ps: P[]) => ps.map(([x, y]) => `${X(x)},${Y(y)}`).join(' ');
  const text = (ps: P[]) => ps.map(([x, y]) => `(${x}, ${y})`).join(', ');
  return (
    <SimFrame title="Slide, flip and turn" task={task} simId={simId} done={done} onReset={() => setMoves([])}
      controls={<div className={s.ops} role="group" aria-label="Moves">
        {MOVES.map((m) => <button key={m.label} type="button" className={s.op} onClick={() => setMoves((a) => [...a, m.move].slice(-30))}>{m.label}</button>)}
        <button type="button" className={s.op} disabled={!moves.length} onClick={() => setMoves((a) => a.slice(0, -1))}>Undo</button></div>}
      readout={<>Corners now: {text(now)}. {moves.length} move{moves.length === 1 ? '' : 's'} so far.{target && !done && <> Target corners: {text(target)}.</>}</>}>
      <svg viewBox="0 0 300 260" className={s.plot} role="img" aria-label={`A triangle on a grid with corners ${text(now)}.${target ? ' A target triangle is shown as a dashed outline.' : ''}`}>
        {Array.from({ length: 17 }, (_, i) => i - 8).map((i) => <g key={i} opacity={i === 0 ? 0.9 : 0.2}><line x1={X(i)} y1={Y(-8)} x2={X(i)} y2={Y(8)} stroke="currentColor" strokeWidth={i === 0 ? 1.5 : 0.7} /><line x1={X(-8)} y1={Y(i)} x2={X(8)} y2={Y(i)} stroke="currentColor" strokeWidth={i === 0 ? 1.5 : 0.7} /></g>)}
        {target && <polygon points={poly(target)} fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="5 4" />}
        <polygon points={poly(now)} fill="var(--hi, #ffb800)" fillOpacity=".6" stroke="currentColor" strokeWidth="2.5" />
      </svg>
    </SimFrame>
  );
}
