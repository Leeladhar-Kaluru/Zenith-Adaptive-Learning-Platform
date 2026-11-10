import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { track } from '../../track/tracker';
import s from './sims.module.css';

/** A spinner with equal parts. Spin it many times and compare what happens with what the maths predicts. */
export function SpinnerSim({ blockId, parts: p0 = 6, hit: h0 = 2, task = '' }: { blockId: string; parts?: number; hit?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [parts, setParts] = useState(clamp(p0, 2, 12));
  const [hit, setHit] = useState(clamp(h0, 1, Math.min(11, parts - 1)));
  const [trials, setTrials] = useState(0);
  const [hits, setHits] = useState(0);
  const h = Math.min(hit, parts - 1);
  const theory = h / parts;
  const empirical = trials ? hits / trials : 0;
  const done = trials >= 200 && Math.abs(empirical - theory) <= 0.05;

  function spin(times: number) {
    let got = 0;
    for (let i = 0; i < times; i++) if (Math.floor(Math.random() * parts) < h) got++;
    setTrials((t) => t + times);
    setHits((x) => x + got);
    track('sim_change', 'sim', simId, { spins: times, parts, hit: h });
  }
  const reset = () => { setTrials(0); setHits(0); };
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <SimFrame title="Spin and compare" task={task || 'Spin at least 200 times. How close does the experiment get to what maths predicts?'} simId={simId} done={done} onReset={reset}
      controls={<>
        <Slider id="parts" label="Equal parts" value={parts} min={2} max={12} simId={simId} onChange={(v) => { setParts(v); reset(); }} />
        <Slider id="hit" label="Winning parts" value={h} min={1} max={Math.max(1, parts - 1)} simId={simId} onChange={(v) => { setHit(v); reset(); }} />
        <div className={s.ops}>{[1, 10, 100].map((k) => <button key={k} type="button" className={s.op} onClick={() => spin(k)}>Spin {k}x</button>)}</div></>}
      readout={trials ? `${hits} wins in ${trials} spins = ${pct(empirical)}. Maths says ${h}/${parts} = ${pct(theory)}.` : `Maths says ${h}/${parts} = ${pct(theory)}. Spin to test it.`}>
      <svg viewBox="0 0 120 120" className={s.spinner} role="img" aria-label={`Spinner with ${parts} equal parts, ${h} winning`}>
        {Array.from({ length: parts }, (_, i) => {
          const a0 = (i / parts) * 2 * Math.PI - Math.PI / 2, a1 = ((i + 1) / parts) * 2 * Math.PI - Math.PI / 2;
          const d = `M60 60 L${60 + 54 * Math.cos(a0)} ${60 + 54 * Math.sin(a0)} A54 54 0 0 1 ${60 + 54 * Math.cos(a1)} ${60 + 54 * Math.sin(a1)} Z`;
          return <path key={i} d={d} className={i < h ? s.win : s.lose} />;
        })}
      </svg>
      <div className={s.bars} aria-hidden="true">
        <div><span>Experiment</span><i style={{ width: pct(empirical) }} className={s.barA} /></div>
        <div><span>Maths</span><i style={{ width: pct(theory) }} className={s.barB} /></div>
      </div>
    </SimFrame>
  );
}
