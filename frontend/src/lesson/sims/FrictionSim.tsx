import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { slope } from './physics';
import s from './sims.module.css';

const SURFACES = [{ id: 'ice', name: 'Ice', mu: 0.05 }, { id: 'wood', name: 'Wood', mu: 0.4 }, { id: 'rubber', name: 'Rubber', mu: 0.9 }] as const;
const nearest = (mu: number) => SURFACES.reduce((a, m) => (Math.abs(m.mu - mu) < Math.abs(a.mu - mu) ? m : a)).id;

/** A block on a ramp: the pull down the slope against friction. It stays still until the ramp is steeper than the critical angle. */
export function FrictionSim({ blockId, mass0 = 2, angle0 = 20, mu0 = 0.4, goal_angle, task = '' }: { blockId: string; mass0?: number; angle0?: number; mu0?: number; goal_angle?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [mass, setMass] = useState(clamp(mass0, 1, 50));
  const [angle, setAngle] = useState(clamp(angle0, 0, 80));
  const [surface, setSurface] = useState<string>(nearest(clamp(mu0, 0.05, 0.9)));
  const mu = SURFACES.find((x) => x.id === surface)!.mu;
  const r = slope({ mass, angle, mu });
  const done = goal_angle !== undefined && r.slides && angle >= goal_angle - 1 && angle <= goal_angle + 1;
  const a = (angle * Math.PI) / 180, x0 = 30, y0 = 190, len = 240;
  const top = { x: x0 + len * Math.cos(a), y: y0 - len * Math.sin(a) };
  const at = r.slides ? 0.62 : 0.5;                       // the block sits lower on the ramp once it slides
  const bx = x0 + len * Math.cos(a) * at, by = y0 - len * Math.sin(a) * at;
  return (
    <SimFrame title="Block on a ramp" task={task} simId={simId} done={done} onReset={() => { setMass(clamp(mass0, 1, 50)); setAngle(clamp(angle0, 0, 80)); setSurface(nearest(clamp(mu0, 0.05, 0.9))); }}
      controls={<>
        <Slider id="angle" label="Ramp angle (°)" value={angle} min={0} max={80} simId={simId} onChange={setAngle} />
        <Slider id="mass" label="Mass (kg)" value={mass} min={1} max={50} simId={simId} onChange={setMass} />
        <div className={s.ops} role="group" aria-label="Surface">{SURFACES.map((m) => <button key={m.id} type="button" className={s.op} aria-pressed={surface === m.id} onClick={() => setSurface(m.id)}>{m.name}</button>)}</div></>}
      readout={<>
        Pull down the ramp = {r.along.toFixed(1)} N. The most friction can hold = {r.maxStatic.toFixed(1)} N (μ = {mu}).{' '}
        {r.slides ? <strong>The block slides with acceleration {r.accel.toFixed(2)} m/s².</strong> : <strong>The block stays still: friction matches the pull ({r.friction.toFixed(1)} N).</strong>}{' '}
        It starts to slide above {r.critical.toFixed(1)}°.{goal_angle !== undefined && <> Aim for about {goal_angle}°.</>}
      </>}>
      <svg viewBox="0 0 300 220" className={s.plot} role="img" aria-label={`A ${mass} kilogram block on a ${surface} ramp tilted ${angle.toFixed(0)} degrees. ${r.slides ? 'It slides down.' : 'It stays still.'}`}>
        <polygon points={`${x0},${y0} ${top.x},${y0} ${top.x},${top.y}`} fill="#8a6a3a" opacity=".35" stroke="currentColor" strokeWidth="2" />
        <g transform={`translate(${bx} ${by}) rotate(${-angle})`}><rect x="-14" y="-24" width="28" height="24" fill="var(--hi, #ffb800)" stroke="currentColor" strokeWidth="2" /></g>
        <text x="12" y="212" fontSize="11" fill="currentColor">{angle.toFixed(0)}°</text>
      </svg>
    </SimFrame>
  );
}
