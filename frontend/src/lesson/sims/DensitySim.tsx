import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import s from './sims.module.css';

const LIQUIDS = [
  { id: 'oil', name: 'Oil', d: 0.8, color: '#f6c453' },
  { id: 'water', name: 'Water', d: 1.0, color: '#6cb7ff' },
  { id: 'salt', name: 'Salt water', d: 1.2, color: '#8f9bff' },
] as const;

/** Density = mass / volume. An object floats when it is less dense than the liquid. Change the mass, the volume and the liquid. */
export function DensitySim({ blockId, mass0 = 60, vol0 = 50, goal, task = '' }: { blockId: string; mass0?: number; vol0?: number; goal?: string; task?: string }) {
  const simId = useSimId(blockId);
  const [mass, setMass] = useState(clamp(mass0, 1, 500));
  const [vol, setVol] = useState(clamp(vol0, 1, 200));
  const [liq, setLiq] = useState<(typeof LIQUIDS)[number]['id']>('water');
  const liquid = LIQUIDS.find((l) => l.id === liq)!;
  const density = mass / vol;
  const state = Math.abs(density - liquid.d) < 0.005 ? 'hover' : density < liquid.d ? 'float' : 'sink';
  const done = (goal === 'float' && state === 'float') || (goal === 'sink' && state === 'sink');
  // How much of the object is under the surface when it floats: density / liquid density.
  const sub = Math.min(1, density / liquid.d);
  const size = 28 + Math.min(40, Math.sqrt(vol) * 3);
  const top = state === 'sink' ? 150 - size : state === 'hover' ? 80 : 60 - size * (1 - sub) + 20;
  const verdict = state === 'float' ? `Floats: ${density.toFixed(2)} g/cm³ is less than ${liquid.d.toFixed(1)}` : state === 'sink' ? `Sinks: ${density.toFixed(2)} g/cm³ is more than ${liquid.d.toFixed(1)}` : 'Hovers: same density as the liquid';

  return (
    <SimFrame title="Float or sink?" task={task} simId={simId} done={done} onReset={() => { setMass(clamp(mass0, 1, 500)); setVol(clamp(vol0, 1, 200)); setLiq('water'); }}
      controls={<>
        <Slider id="mass" label="Mass (g)" value={mass} min={1} max={500} simId={simId} onChange={setMass} />
        <Slider id="vol" label="Volume (cm³)" value={vol} min={1} max={200} simId={simId} onChange={setVol} />
        <div className={s.ops} role="group" aria-label="Liquid">
          {LIQUIDS.map((l) => <button key={l.id} type="button" className={s.op} aria-pressed={liq === l.id} style={liq === l.id ? { background: 'var(--brand-soft)' } : undefined} onClick={() => setLiq(l.id)}>{l.name}</button>)}
        </div></>}
      readout={`Density = ${mass} ÷ ${vol} = ${density.toFixed(2)} g/cm³. ${verdict}.`}>
      <svg viewBox="0 0 220 180" className={s.plot} role="img" aria-label={`A block with density ${density.toFixed(2)} in ${liquid.name}: it ${state === 'hover' ? 'hovers' : state === 'float' ? 'floats' : 'sinks'}`}>
        <rect x="10" y="60" width="200" height="110" fill={liquid.color} opacity=".55" />
        <rect x="10" y="20" width="200" height="150" fill="none" stroke="currentColor" strokeWidth="3" />
        <rect x={110 - size / 2} y={top} width={size} height={size} rx="4" fill="#c97b3f" stroke="#14193a" strokeWidth="3" style={{ transition: 'y .4s ease' }} />
      </svg>
    </SimFrame>
  );
}
