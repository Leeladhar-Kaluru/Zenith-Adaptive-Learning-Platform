import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { snell } from './physics';
import s from './sims.module.css';

const MEDIA = [{ id: 'air', name: 'Air', n: 1.0 }, { id: 'water', name: 'Water', n: 1.33 }, { id: 'glass', name: 'Glass', n: 1.5 }, { id: 'diamond', name: 'Diamond', n: 2.42 }] as const;
const nearest = (n: number) => MEDIA.reduce((a, m) => (Math.abs(m.n - n) < Math.abs(a.n - n) ? m : a)).id;
const C = 150, Y = 120, L = 100;

/** Light crossing from one material into another: Snell's law, the critical angle and total internal reflection, with Fresnel brightness. */
export function RefractionSim({ blockId, n1 = 1, n2 = 1.5, angle0 = 30, goal, goal_angle, task = '' }: { blockId: string; n1?: number; n2?: number; angle0?: number; goal?: string; goal_angle?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [top, setTop] = useState<string>(nearest(clamp(n1, 1, 2.5)));
  const [bottom, setBottom] = useState<string>(nearest(clamp(n2, 1, 2.5)));
  const [angle, setAngle] = useState(clamp(angle0, 0, 89));
  const A = MEDIA.find((m) => m.id === top)!, B = MEDIA.find((m) => m.id === bottom)!;
  const r = snell({ n1: A.n, n2: B.n, angle });
  const done = (goal === 'tir' && r.tir) || (goal_angle !== undefined && r.refracted !== null && Math.abs(r.refracted - goal_angle) <= 1);
  const end = (deg: number, dir: 1 | -1, down: boolean) => ({ x: C + dir * Math.sin((deg * Math.PI) / 180) * L, y: Y + (down ? 1 : -1) * Math.cos((deg * Math.PI) / 180) * L });
  const inc = end(angle, -1, false), refl = end(angle, 1, false), ref = r.refracted === null ? null : end(r.refracted, 1, true);
  const medium = (name: string, n: number) => `${name} (n = ${n})`;

  return (
    <SimFrame title="Bend the light" task={task} simId={simId} done={done} onReset={() => { setTop(nearest(clamp(n1, 1, 2.5))); setBottom(nearest(clamp(n2, 1, 2.5))); setAngle(clamp(angle0, 0, 89)); }}
      controls={<>
        <Slider id="angle" label="Angle of incidence (°)" value={angle} min={0} max={89} simId={simId} onChange={setAngle} />
        <div className={s.ops} role="group" aria-label="Upper material">{MEDIA.map((m) => <button key={m.id} type="button" className={s.op} aria-pressed={top === m.id} onClick={() => setTop(m.id)}>Top: {m.name}</button>)}</div>
        <div className={s.ops} role="group" aria-label="Lower material">{MEDIA.map((m) => <button key={m.id} type="button" className={s.op} aria-pressed={bottom === m.id} onClick={() => setBottom(m.id)}>Bottom: {m.name}</button>)}</div></>}
      readout={<>
        Light goes from {medium(A.name, A.n)} into {medium(B.name, B.n)}. n₁ sin θ₁ = n₂ sin θ₂, so {A.n} × sin {angle.toFixed(0)}° = {B.n} × sin θ₂.{' '}
        {r.tir ? <strong>Total internal reflection: no light gets through.</strong> : <>Refracted angle θ₂ = {r.refracted!.toFixed(1)}°. The ray bends {B.n > A.n ? 'toward' : B.n < A.n ? 'away from' : 'neither toward nor away from'} the normal. About {(r.reflectance * 100).toFixed(1)}% reflects.</>}
        {r.critical !== null && <> Critical angle {r.critical.toFixed(1)}°.</>}
        {goal_angle !== undefined && <> Aim for θ₂ = {goal_angle}°.</>}
      </>}>
      <svg viewBox="0 0 300 240" className={s.plot} role="img" aria-label={`A light ray hits the boundary between ${A.name} and ${B.name} at ${angle} degrees. ${r.tir ? 'It is totally reflected.' : `It refracts to ${r.refracted!.toFixed(1)} degrees.`}`}>
        <rect x="0" y="0" width="300" height={Y} fill="#cfe8ff" opacity={0.25 + (A.n - 1) * 0.25} />
        <rect x="0" y={Y} width="300" height={240 - Y} fill="#6cb7ff" opacity={0.25 + (B.n - 1) * 0.25} />
        <line x1="0" y1={Y} x2="300" y2={Y} stroke="currentColor" strokeWidth="3" />
        <line x1={C} y1="10" x2={C} y2="230" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" opacity=".7" />
        <line x1={inc.x} y1={inc.y} x2={C} y2={Y} stroke="var(--hi, #ffb800)" strokeWidth="4" strokeLinecap="round" />
        <line x1={C} y1={Y} x2={refl.x} y2={refl.y} stroke="var(--hi, #ffb800)" strokeWidth="4" strokeLinecap="round" opacity={Math.max(0.15, r.reflectance)} />
        {ref && <line x1={C} y1={Y} x2={ref.x} y2={ref.y} stroke="var(--hi, #ffb800)" strokeWidth="4" strokeLinecap="round" />}
        <text x="8" y="16" fontSize="11" fill="currentColor">{A.name}</text><text x="8" y="232" fontSize="11" fill="currentColor">{B.name}</text>
        <text x={C + 6} y="18" fontSize="10" fill="currentColor">normal</text>
      </svg>
    </SimFrame>
  );
}
