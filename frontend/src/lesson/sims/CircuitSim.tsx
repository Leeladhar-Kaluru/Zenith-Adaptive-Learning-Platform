import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { circuit } from './physics';
import s from './sims.module.css';

const f = (n: number, d = 2) => (Number.isFinite(n) ? n.toFixed(d).replace(/\.?0+$/, '') : '0');

/** Two resistors on a battery, in series or in parallel. Ohm's law (V = I R) gives every number you see. */
export function CircuitSim({ blockId, volts: v0 = 6, r1: a0 = 2, r2: b0 = 4, mode: m0 = 'series', goal_current, task = '' }: { blockId: string; volts?: number; r1?: number; r2?: number; mode?: string; goal_current?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [volts, setVolts] = useState(clamp(v0, 1, 24));
  const [r1, setR1] = useState(clamp(a0, 1, 100));
  const [r2, setR2] = useState(clamp(b0, 1, 100));
  const [mode, setMode] = useState<'series' | 'parallel'>(m0 === 'parallel' ? 'parallel' : 'series');
  const c = circuit({ volts, r1, r2, mode });
  const done = goal_current !== undefined && Math.abs(c.current - goal_current) <= Math.max(0.02, goal_current * 0.03);
  const speed = Math.max(0.4, Math.min(6, 6 / (c.current + 0.5)));            // seconds per lap: a bigger current flows faster
  const [b1, b2] = c.branches;

  return (
    <SimFrame title="Build a circuit" task={task} simId={simId} done={done} onReset={() => { setVolts(clamp(v0, 1, 24)); setR1(clamp(a0, 1, 100)); setR2(clamp(b0, 1, 100)); setMode(m0 === 'parallel' ? 'parallel' : 'series'); }}
      controls={<>
        <Slider id="volts" label="Battery (V)" value={volts} min={1} max={24} simId={simId} onChange={setVolts} />
        <Slider id="r1" label="Resistor R₁ (Ω)" value={r1} min={1} max={100} simId={simId} onChange={setR1} />
        <Slider id="r2" label="Resistor R₂ (Ω)" value={r2} min={1} max={100} simId={simId} onChange={setR2} />
        <div className={s.ops} role="group" aria-label="How the resistors are joined">
          {(['series', 'parallel'] as const).map((m) => <button key={m} type="button" className={s.op} aria-pressed={mode === m} onClick={() => setMode(m)}>{m === 'series' ? 'In series' : 'In parallel'}</button>)}
        </div></>}
      readout={<>
        {mode === 'series' ? `R = R₁ + R₂ = ${r1} + ${r2} = ${f(c.total)} Ω` : `1/R = 1/R₁ + 1/R₂, so R = ${f(c.total)} Ω`}. Current from the battery I = V ÷ R = {volts} ÷ {f(c.total)} = {f(c.current)} A.{' '}
        R₁: {f(b1.v)} V, {f(b1.i)} A, {f(b1.p)} W. R₂: {f(b2.v)} V, {f(b2.i)} A, {f(b2.p)} W. Power drawn {f(c.power)} W.
        {goal_current !== undefined && <> Aim for a battery current of {goal_current} A.</>}
      </>}>
      <svg viewBox="0 0 320 190" className={s.plot} role="img" aria-label={`A ${volts} volt battery with ${r1} ohm and ${r2} ohm resistors in ${mode}. Battery current ${f(c.current)} amperes.`}>
        <style>{`.flow{stroke-dasharray:6 10;animation:zflow ${speed}s linear infinite}@keyframes zflow{to{stroke-dashoffset:-16}}@media (prefers-reduced-motion:reduce){.flow{animation:none}}`}</style>
        {/* wires */}
        <g fill="none" stroke="currentColor" strokeWidth="3">
          {mode === 'series'
            ? <path d="M40 150 V40 H100 M140 40 H180 M220 40 H280 V150 H40" />
            : <path d="M40 150 V40 H110 M110 40 H250 M110 40 V60 M250 40 V60 M110 120 V150 M250 120 V150 M40 150 H280 M280 40 V150 M250 40 H280" />}
        </g>
        <g fill="none" stroke="var(--hi, #ffb800)" strokeWidth="3" className="flow" strokeLinecap="round">
          {mode === 'series' ? <path d="M40 150 V40 H280 V150 H40" /> : <path d="M40 150 V40 H280 V150 H40" />}
        </g>
        {/* battery */}
        <rect x="26" y="80" width="28" height="30" fill="var(--surface, #fff)" />
        <line x1="30" y1="86" x2="50" y2="86" stroke="currentColor" strokeWidth="4" /><line x1="36" y1="102" x2="44" y2="102" stroke="currentColor" strokeWidth="4" />
        <text x="58" y="98" fontSize="11" fill="currentColor">{volts} V</text>
        {/* resistors */}
        {mode === 'series' ? (<>
          <rect x="100" y="28" width="40" height="24" rx="4" fill="var(--surface-2, #eee)" stroke="currentColor" strokeWidth="3" /><text x="120" y="45" textAnchor="middle" fontSize="11" fill="currentColor">{r1}Ω</text>
          <rect x="180" y="28" width="40" height="24" rx="4" fill="var(--surface-2, #eee)" stroke="currentColor" strokeWidth="3" /><text x="200" y="45" textAnchor="middle" fontSize="11" fill="currentColor">{r2}Ω</text>
        </>) : (<>
          <rect x="98" y="60" width="24" height="60" rx="4" fill="var(--surface-2, #eee)" stroke="currentColor" strokeWidth="3" /><text x="110" y="95" textAnchor="middle" fontSize="11" fill="currentColor">{r1}</text>
          <rect x="238" y="60" width="24" height="60" rx="4" fill="var(--surface-2, #eee)" stroke="currentColor" strokeWidth="3" /><text x="250" y="95" textAnchor="middle" fontSize="11" fill="currentColor">{r2}</text>
        </>)}
        <text x="160" y="178" textAnchor="middle" fontSize="11" fill="currentColor">I = {f(c.current)} A</text>
      </svg>
    </SimFrame>
  );
}
