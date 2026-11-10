import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { Icon } from '../icons/Icon';
import { Button } from '../ui/kit';
import s from './fx.module.css';

/** Suspense fallback / route transition screen: a dot climbs the peak and plants a flag. */
export function RouteLoader({ label = 'Loading' }: { label?: string }) {
  return (
    <div className={s.loader} role="status" aria-live="polite">
      <svg viewBox="0 0 110 96" aria-hidden="true">
        <path className={s.mt} d="M4 90 L52 28 L72 56 L98 14 L108 90 Z" />
        <path className={s.route} d="M12 84 L52 40 L72 62 L98 20" />
        <path className={s.flag} d="M98 20 V4 l12 4 -12 4" />
        <circle className={s.dot} r="6" />
      </svg>
      <p className="hand">{label}…</p>
    </div>
  );
}

interface Celebration { title: string; text?: string; icon?: string; cta?: string; onClose?: () => void }
interface Fx {
  xp: (n: number) => void;
  confetti: () => void;
  celebrate: (c: Celebration) => void;
}
const FxCtx = createContext<Fx>({ xp() {}, confetti() {}, celebrate() {} });
export const useFx = () => useContext(FxCtx);

const COLORS = ['#ffd43b', '#3a46d6', '#12a57f', '#e0345f', '#ff8a3d'];
const reduced = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function FxProvider({ children }: { children: ReactNode }) {
  const [floaters, setFloaters] = useState<Array<{ id: number; n: number }>>([]);
  const [conf, setConf] = useState<number | null>(null);
  const [cele, setCele] = useState<Celebration | null>(null);

  const xp = useCallback((n: number) => {
    const id = Date.now() + Math.random();
    setFloaters((f) => [...f, { id, n }]);
    setTimeout(() => setFloaters((f) => f.filter((x) => x.id !== id)), 1300);
  }, []);
  const confetti = useCallback(() => {
    if (reduced()) return;
    const id = Date.now();
    setConf(id);
    setTimeout(() => setConf((c) => (c === id ? null : c)), 3200);
  }, []);
  const celebrate = useCallback((c: Celebration) => { setCele(c); confetti(); }, [confetti]);
  const value = useMemo(() => ({ xp, confetti, celebrate }), [xp, confetti, celebrate]);

  const pieces = useMemo(
    () => Array.from({ length: 42 }, (_, i) => ({
      x: `${Math.round(Math.random() * 100)}%`, dx: `${Math.round(Math.random() * 160 - 80)}px`,
      d: `${(Math.random() * 0.5).toFixed(2)}s`, t: `${(2 + Math.random() * 1.2).toFixed(2)}s`,
      r: `${Math.round(Math.random() * 360)}deg`, c: COLORS[i % COLORS.length],
    })),
    // regenerate per burst
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conf],
  );

  return (
    <FxCtx.Provider value={value}>
      {children}
      {floaters.map((f) => (
        <div key={f.id} className={s.floater} aria-hidden="true"><Icon name="bolt" size={34} />+{f.n} XP</div>
      ))}
      {conf !== null && (
        <div className={s.confetti} aria-hidden="true">
          {pieces.map((p, i) => (
            <i key={i} style={{ ['--x' as string]: p.x, ['--dx' as string]: p.dx, ['--d' as string]: p.d, ['--t' as string]: p.t, ['--r' as string]: p.r, ['--c' as string]: p.c } as React.CSSProperties} />
          ))}
        </div>
      )}
      {cele && (
        <div className={s.overlay} role="dialog" aria-modal="true" aria-label={cele.title}>
          <div className={s.cele}>
            <div className={s.badge}><Icon name={cele.icon ?? 'trophy'} size={54} /></div>
            <h2>{cele.title}</h2>
            {cele.text && <p className="muted">{cele.text}</p>}
            <Button variant="brand" onClick={() => { cele.onClose?.(); setCele(null); }}>{cele.cta ?? 'Keep climbing'}</Button>
          </div>
        </div>
      )}
    </FxCtx.Provider>
  );
}
