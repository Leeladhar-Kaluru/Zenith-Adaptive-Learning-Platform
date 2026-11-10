import { useState } from 'react';
import { Button } from '../ui/kit';
import { Icon } from '../icons/Icon';
import s from './lesson.module.css';

const neg = (n: number) => (n < 0 ? `−${-n}` : String(n));

/* Number line: hop left and right and watch the equation. */
export function NumberLine({ start = 0, min = -6, max = 6 }: { start?: number; min?: number; max?: number }) {
  const [pos, setPos] = useState(start);
  const [note, setNote] = useState('start');
  const pct = (v: number) => ((v - min) / (max - min)) * 100;
  const move = (d: number) => { setPos((p) => Math.max(min, Math.min(max, p + d))); setNote(d < 0 ? '← left' : 'right →'); };
  const ticks = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  return (
    <figure className={s.widget} aria-label="Interactive number line">
      <div className={s.nl}>
        <div className={s.nlLine} />
        {ticks.map((v) => (
          <div key={v} className={`${s.tk} ${v === 0 ? s.tkZero : ''}`} style={{ left: `${pct(v)}%` }}><i>{neg(v)}</i></div>
        ))}
        <div className={s.hop} style={{ left: `${pct(pos)}%` }} aria-hidden="true">{note}</div>
        <div className={s.me} style={{ left: `${pct(pos)}%` }} />
      </div>
      <div className={s.ctrl}>
        <Button variant="ghost" size="sm" onClick={() => move(-1)} icon="minus" aria-label="Move one step left">1</Button>
        <Button variant="ghost" size="sm" onClick={() => move(1)} icon="plus" aria-label="Move one step right">1</Button>
        <button className={s.reset} onClick={() => { setPos(start); setNote('start'); }} aria-label="Reset"><Icon name="refresh" size={20} /></button>
        <output className={s.eq} aria-live="polite">You are at {neg(pos)}</output>
      </div>
      <p className="hand">tap − five times and watch where you land</p>
    </figure>
  );
}

/* Balance scale for x + a = b: remove the same from both sides. */
export function Balance({ a = 3, b = 7 }: { a?: number; b?: number }) {
  const [rem, setRem] = useState(0);
  const left = a - rem, right = b - rem;
  const solved = left === 0;
  const tilt = solved ? 0 : (a - b) * 0; // always level: it is an equation
  return (
    <figure className={s.widget} aria-label="Interactive balance">
      <div className={s.scale} style={{ transform: `rotate(${tilt}deg)` }}>
        <div className={s.pan}><span className={s.xBox}>x</span>{Array.from({ length: Math.max(0, left) }, (_, i) => <i key={i} className={s.unit} />)}</div>
        <div className={s.beam} />
        <div className={s.pan}>{Array.from({ length: Math.max(0, right) }, (_, i) => <i key={i} className={s.unit} />)}</div>
      </div>
      <div className={s.ctrl}>
        <Button variant="ghost" size="sm" disabled={solved} onClick={() => setRem((r) => r + 1)} icon="minus">Take 1 from both sides</Button>
        <button className={s.reset} onClick={() => setRem(0)} aria-label="Reset"><Icon name="refresh" size={20} /></button>
        <output className={s.eq} aria-live="polite">{solved ? `x = ${right}` : `x + ${left} = ${right}`}</output>
      </div>
      <p className="hand">keep the scale balanced: whatever you do to one side, do to the other</p>
    </figure>
  );
}

/* Fraction bar. */
export function Fraction({ num = 1, den = 4 }: { num?: number; den?: number }) {
  const [n, setN] = useState(num);
  return (
    <figure className={s.widget} aria-label="Interactive fraction bar">
      <div className={s.fbar} style={{ ['--den' as string]: den } as React.CSSProperties}>
        {Array.from({ length: den }, (_, i) => <i key={i} className={i < n ? s.fOn : ''} />)}
      </div>
      <div className={s.ctrl}>
        <Button variant="ghost" size="sm" icon="minus" disabled={n <= 0} onClick={() => setN((x) => x - 1)} aria-label="Fewer parts">1</Button>
        <Button variant="ghost" size="sm" icon="plus" disabled={n >= den} onClick={() => setN((x) => x + 1)} aria-label="More parts">1</Button>
        <output className={s.eq} aria-live="polite">{n}/{den}</output>
      </div>
    </figure>
  );
}
