import { useEffect, useState, type ReactNode } from 'react';
import { track, trackThrottled } from '../../track/tracker';
import { Icon } from '../../icons/Icon';
import s from './sims.module.css';

export const clamp = (v: number, lo: number, hi: number) => (Number.isFinite(v) ? Math.max(lo, Math.min(hi, v)) : lo);

/** Where this simulation lives, so every move can be tied to the lesson. */
export function useSimId(blockId: string) {
  const lesson = typeof location !== 'undefined' ? location.pathname.split('/').filter(Boolean).pop() ?? 'lesson' : 'lesson';
  return `${lesson}:${blockId}`;
}

interface FrameProps {
  title: string; task: string; simId: string; done: boolean; children: ReactNode; controls: ReactNode; readout: ReactNode; onReset: () => void;
}

/** Shared chrome: the challenge strip, the controls, a live readout and a reset. Logs resets and the first completion. */
export function SimFrame({ title, task, simId, done, children, controls, readout, onReset }: FrameProps) {
  const [wasDone, setWasDone] = useState(false);
  useEffect(() => { if (done && !wasDone) { setWasDone(true); track('sim_change', 'sim', simId, { goalReached: true }); } }, [done, wasDone, simId]);
  return (
    <figure className={s.sim} aria-label={`Interactive: ${title}`}>
      <figcaption className={s.head}><span className={s.tag}><Icon name="spark" size={16} /> Try it</span><b>{title}</b></figcaption>
      {task && <p className={`${s.task} ${done ? s.taskDone : ''}`} role="status">{done ? <><Icon name="check" size={18} accent="var(--ok)" /> Done. {task}</> : <>Challenge: {task}</>}</p>}
      <div className={s.stage}>{children}</div>
      <div className={s.controls}>{controls}</div>
      <div className={s.foot}>
        <output className={s.readout} aria-live="polite">{readout}</output>
        <button type="button" className={s.reset} onClick={() => { track('sim_reset', 'sim', simId); onReset(); }} aria-label="Reset the simulation"><Icon name="refresh" size={20} /></button>
      </div>
    </figure>
  );
}

interface SliderProps { id: string; label: string; value: number; min: number; max: number; step?: number; simId: string; onChange: (v: number) => void; text?: (v: number) => string }

/** Keyboard-accessible slider that reports each change (throttled) as a student move. */
export function Slider({ id, label, value, min, max, step = 1, simId, onChange, text }: SliderProps) {
  return (
    <label className={s.slider} htmlFor={`${simId}-${id}`}>
      <span>{label}: <b>{text ? text(value) : value}</b></span>
      <input id={`${simId}-${id}`} type="range" min={min} max={max} step={step} value={value} aria-valuetext={text ? text(value) : String(value)}
        onChange={(e) => { const v = clamp(Number(e.target.value), min, max); onChange(v); trackThrottled(`${simId}:${id}`, 400, 'sim_change', 'sim', simId, { name: id, value: v }); }} />
    </label>
  );
}
