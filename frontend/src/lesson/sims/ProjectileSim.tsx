import { useEffect, useMemo, useRef, useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { projectile } from './physics';
import s from './sims.module.css';

const WORLDS = [{ id: 'earth', name: 'Earth', g: 9.8 }, { id: 'mars', name: 'Mars', g: 3.7 }, { id: 'moon', name: 'Moon', g: 1.6 }, { id: 'jupiter', name: 'Jupiter', g: 24.8 }] as const;
const W = 320, H = 190, PAD = 22;

/** Projectile motion without air resistance. Fire it, or step through the flight. The numbers come straight from the equations of motion. */
export function ProjectileSim({ blockId, v0 = 20, angle0 = 45, g0 = 9.8, h0 = 0, target, tol, task = '' }: { blockId: string; v0?: number; angle0?: number; g0?: number; h0?: number; target?: number; tol?: number; task?: string }) {
  const simId = useSimId(blockId);
  const [v, setV] = useState(clamp(v0, 1, 60));
  const [angle, setAngle] = useState(clamp(angle0, 0, 90));
  const [g, setG] = useState(clamp(g0, 1, 25));
  const [h, setH] = useState(clamp(h0, 0, 50));
  const [t, setT] = useState<number | null>(null);       // null = nothing launched yet
  const [playing, setPlaying] = useState(false);
  const [landed, setLanded] = useState<number | null>(null);
  const raf = useRef(0);

  const p = useMemo(() => projectile({ v, angle, g, h0: h }), [v, angle, g, h]);
  const xMax = Math.max(p.range * 1.1, (target ?? 0) * 1.15, 10), yMax = Math.max(p.maxHeight * 1.25, 5);
  const sx = (x: number) => PAD + (x / xMax) * (W - PAD * 2), sy = (y: number) => H - PAD - (y / yMax) * (H - PAD * 2);
  const path = p.points.map((q) => `${sx(q.x).toFixed(1)},${sy(q.y).toFixed(1)}`).join(' ');

  // any change to the launch cancels the flight in progress
  useEffect(() => { cancelAnimationFrame(raf.current); setPlaying(false); setT(null); setLanded(null); }, [v, angle, g, h]);
  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  const land = () => { setT(p.time); setLanded(p.range); setPlaying(false); };
  const fire = () => {
    cancelAnimationFrame(raf.current);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { land(); return; }
    setPlaying(true); setLanded(null);
    const t0 = performance.now(), speed = Math.max(1, p.time / 3);        // a long flight is sped up so it never takes more than about 3 s
    const tick = (now: number) => {
      const tt = ((now - t0) / 1000) * speed;
      if (tt >= p.time) { land(); return; }
      setT(tt); raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  };
  const step = () => {
    cancelAnimationFrame(raf.current); setPlaying(false);
    const next = Math.min(p.time, (t ?? 0) + 0.25);
    setT(next); if (next >= p.time) setLanded(p.range);
  };

  const now = t ?? 0;
  const vx = v * Math.cos((angle * Math.PI) / 180), vy0 = v * Math.sin((angle * Math.PI) / 180);
  const x = vx * now, y = Math.max(0, h + vy0 * now - 0.5 * g * now * now), vy = vy0 - g * now, speedNow = Math.hypot(vx, vy);
  const hit = target !== undefined && tol !== undefined && landed !== null && Math.abs(landed - target) <= tol;
  const world = WORLDS.find((w) => Math.abs(w.g - g) < 0.05)?.name;

  return (
    <SimFrame title="Launch it" task={task} simId={simId} done={hit} onReset={() => { setV(clamp(v0, 1, 60)); setAngle(clamp(angle0, 0, 90)); setG(clamp(g0, 1, 25)); setH(clamp(h0, 0, 50)); }}
      controls={<>
        <Slider id="v" label="Speed (m/s)" value={v} min={1} max={60} simId={simId} onChange={setV} />
        <Slider id="angle" label="Angle (°)" value={angle} min={0} max={90} simId={simId} onChange={setAngle} />
        <Slider id="h" label="Start height (m)" value={h} min={0} max={50} simId={simId} onChange={setH} />
        <div className={s.ops} role="group" aria-label="Where are you?">{WORLDS.map((w) => <button key={w.id} type="button" className={s.op} aria-pressed={world === w.name} onClick={() => setG(w.g)}>{w.name} {w.g}</button>)}</div>
        <div className={s.ops}>
          <button type="button" className={s.op} onClick={fire} disabled={playing}>Fire</button>
          <button type="button" className={s.op} onClick={step} disabled={playing || landed !== null}>Step 0.25 s</button>
        </div></>}
      readout={<>
        Range {p.range.toFixed(1)} m · highest point {p.maxHeight.toFixed(1)} m · flight time {p.time.toFixed(2)} s.
        {t !== null && <> At t = {now.toFixed(2)} s: x = {x.toFixed(1)} m, height = {y.toFixed(1)} m, speed = {speedNow.toFixed(1)} m/s.</>}
        {target !== undefined && <> Target {target} m (within ±{tol}).{landed !== null && (hit ? ' Hit!' : ` Landed at ${landed.toFixed(1)} m: ${landed < target ? 'too short' : 'too far'}.`)}</>}
      </>}>
      <svg viewBox={`0 0 ${W} ${H}`} className={s.plot} role="img" aria-label={`Path of a projectile launched at ${v} m/s and ${angle} degrees: range ${p.range.toFixed(1)} metres, highest point ${p.maxHeight.toFixed(1)} metres`}>
        <line x1={PAD} y1={sy(0)} x2={W - PAD} y2={sy(0)} stroke="currentColor" strokeWidth="3" />
        {target !== undefined && tol !== undefined && <rect x={sx(Math.max(0, target - tol))} y={sy(0) - 8} width={Math.max(4, sx(target + tol) - sx(Math.max(0, target - tol)))} height="8" fill="var(--ok)" opacity=".8"><title>Target</title></rect>}
        <polyline points={path} fill="none" stroke="var(--brand)" strokeWidth="3" strokeDasharray="5 5" />
        <circle cx={sx(p.apexX)} cy={sy(p.maxHeight)} r="4" fill="var(--hi, #ffb800)" stroke="currentColor"><title>Highest point</title></circle>
        <circle cx={sx(t === null ? 0 : x)} cy={sy(t === null ? h : y)} r="7" fill="var(--gap, #e0345f)" stroke="currentColor" strokeWidth="2" />
        <text x={W - PAD} y={sy(0) + 14} textAnchor="end" fontSize="10" fill="currentColor">{xMax.toFixed(0)} m</text>
      </svg>
    </SimFrame>
  );
}
