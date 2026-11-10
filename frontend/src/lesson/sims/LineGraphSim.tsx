import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import s from './sims.module.css';

const SIZE = 280, RANGE = 10;
const px = (v: number) => SIZE / 2 + (v / RANGE) * (SIZE / 2);
const py = (v: number) => SIZE / 2 - (v / RANGE) * (SIZE / 2);
const neg = (n: number) => (n < 0 ? `−${-n}` : String(n));

function equation(m: number, c: number) {
  const mt = m === 0 ? '' : m === 1 ? 'x' : m === -1 ? '−x' : `${neg(m)}x`;
  const ct = c === 0 ? '' : `${mt && c > 0 ? ' + ' : mt ? ' − ' : c < 0 ? '−' : ''}${mt ? Math.abs(c) : Math.abs(c)}`;
  return `y = ${mt || (c === 0 ? '0' : '')}${ct}`;
}

/** y = mx + c. Slide the slope and the intercept and watch the line; optionally match a target line. */
export function LineGraphSim({ blockId, m0 = 1, c0 = 0, goal_m, goal_c, task = '' }: { blockId: string; m0?: number; c0?: number; goal_m?: number; goal_c?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [m, setM] = useState(clamp(m0, -5, 5));
  const [c, setC] = useState(clamp(c0, -10, 10));
  const hasGoal = goal_m !== undefined && goal_c !== undefined;
  const done = hasGoal && m === goal_m && c === goal_c;
  const line = (mm: number, cc: number) => ({ x1: px(-RANGE), y1: py(-RANGE * mm + cc), x2: px(RANGE), y2: py(RANGE * mm + cc) });
  const root = m !== 0 ? -c / m : null;
  return (
    <SimFrame title="Slope and intercept" task={task} simId={simId} done={done} onReset={() => { setM(clamp(m0, -5, 5)); setC(clamp(c0, -10, 10)); }}
      controls={<><Slider id="m" label="Slope m" value={m} min={-5} max={5} step={0.5} simId={simId} onChange={setM} text={neg} />
        <Slider id="c" label="Intercept c" value={c} min={-10} max={10} step={1} simId={simId} onChange={setC} text={neg} /></>}
      readout={<>{equation(m, c)}{root !== null && Math.abs(root) <= RANGE ? ` · crosses the x-axis at x = ${Number.isInteger(root) ? neg(root) : root.toFixed(1)}` : m === 0 ? ' · a flat line' : ''}</>}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className={s.plot} role="img" aria-label={`Graph of ${equation(m, c)}`}>
        {Array.from({ length: 2 * RANGE + 1 }, (_, i) => i - RANGE).map((v) => (
          <g key={v}><line x1={px(v)} y1={0} x2={px(v)} y2={SIZE} className={v === 0 ? s.axis : s.grid} /><line x1={0} y1={py(v)} x2={SIZE} y2={py(v)} className={v === 0 ? s.axis : s.grid} /></g>
        ))}
        {hasGoal && <line {...line(goal_m!, goal_c!)} className={s.target} />}
        <line {...line(m, c)} className={s.curve} />
        <circle cx={px(0)} cy={py(c)} r={5} className={s.dot} />
      </svg>
    </SimFrame>
  );
}
