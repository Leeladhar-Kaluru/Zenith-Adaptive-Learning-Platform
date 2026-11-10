import {
  createContext, useCallback, useContext, useEffect, useRef, useState,
  type ButtonHTMLAttributes, type CSSProperties, type ReactNode,
} from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../icons/Icon';
import s from './kit.module.css';

const cx = (...a: Array<string | false | undefined | null>) => a.filter(Boolean).join(' ');

/* Button ------------------------------------------------------------------ */
interface BtnProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  variant?: 'primary' | 'brand' | 'ghost' | 'danger';
  size?: 'md' | 'sm';
  block?: boolean;
  loading?: boolean;
  to?: string;
  icon?: string;
  iconRight?: string;
}
export function Button({ variant = 'primary', size = 'md', block, loading, to, icon, iconRight, children, disabled, ...rest }: BtnProps) {
  const cls = cx(s.btn, variant === 'brand' && s.brand, variant === 'ghost' && s.ghost, variant === 'danger' && s.danger, size === 'sm' && s.sm, block && s.block);
  const inner = (
    <>
      {loading ? <span className={s.spin} aria-hidden="true" /> : icon && <Icon name={icon} size={20} />}
      {children}
      {iconRight && !loading && <Icon name={iconRight} size={20} />}
    </>
  );
  if (to) return <Link to={to} className={cls} aria-disabled={disabled}>{inner}</Link>;
  return <button className={cls} disabled={disabled || loading} {...rest}>{inner}</button>;
}

/* Card -------------------------------------------------------------------- */
export function Card({ children, to, lift, flat, dashed, className, style, onClick }: {
  children: ReactNode; to?: string; lift?: boolean; flat?: boolean; dashed?: boolean; className?: string; style?: CSSProperties; onClick?: () => void;
}) {
  const cls = cx(s.card, (lift || to) && s.lift, flat && s.flat, dashed && s.dashed, className);
  if (to) return <Link to={to} className={cls} style={style}>{children}</Link>;
  return <div className={cls} style={style} onClick={onClick}>{children}</div>;
}

/* Chip -------------------------------------------------------------------- */
export function Chip({ children, tone, icon }: { children: ReactNode; tone?: 'hi' | 'ok' | 'gap' | 'soft'; icon?: string }) {
  return (
    <span className={cx(s.chip, tone === 'hi' && s.chipHi, tone === 'ok' && s.chipOk, tone === 'gap' && s.chipGap, tone === 'soft' && s.chipSoft)}>
      {icon && <Icon name={icon} size={16} />}{children}
    </span>
  );
}

/* Segmented control ------------------------------------------------------- */
export function Segmented<T extends string | number>({ options, value, onChange, label }: {
  options: ReadonlyArray<{ value: T; label: ReactNode }>; value: T; onChange: (v: T) => void; label: string;
}) {
  return (
    <div className={s.seg} role="group" aria-label={label}>
      {options.map((o) => (
        <button key={String(o.value)} aria-pressed={o.value === value} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

/* Progress ---------------------------------------------------------------- */
export function Progress({ value, label }: { value: number; label?: string }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = requestAnimationFrame(() => setW(Math.max(0, Math.min(100, value)))); return () => cancelAnimationFrame(t); }, [value]);
  return (
    <div className={s.bar} role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <b style={{ width: `${w}%` }} />
    </div>
  );
}

/* Skeleton / Empty -------------------------------------------------------- */
export function Skeleton({ h = 16, w = '100%', r }: { h?: number; w?: number | string; r?: number }) {
  return <div className={s.skel} style={{ height: h, width: w, borderRadius: r }} aria-hidden="true" />;
}
export function EmptyState({ icon = 'peak', title, text, action }: { icon?: string; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className={s.empty}>
      <div className={s.emptyIcon}><Icon name={icon} size={38} /></div>
      <h3>{title}</h3>
      {text && <p className="muted" style={{ maxWidth: '38ch' }}>{text}</p>}
      {action}
    </div>
  );
}

/* Sheet (modal / bottom sheet) ------------------------------------------- */
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = ''; prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className={s.scrim} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={s.sheet} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <button className={s.close} onClick={onClose} aria-label="Close"><Icon name="close" size={20} /></button>
        <h2 style={{ marginBottom: 14, paddingRight: 48 }}>{title}</h2>
        {children}
      </div>
    </div>
  );
}

/* Toasts ------------------------------------------------------------------ */
type ToastKind = 'ok' | 'err' | 'info';
const ToastCtx = createContext<(msg: string, kind?: ToastKind) => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Array<{ id: number; msg: string; kind: ToastKind }>>([]);
  const push = useCallback((msg: string, kind: ToastKind = 'info') => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x.slice(-2), { id, msg, kind }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4200);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className={s.toasts} role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cx(s.toast, t.kind === 'ok' && s.toastOk, t.kind === 'err' && s.toastErr)}>
            <Icon name={t.kind === 'ok' ? 'check' : t.kind === 'err' ? 'warn' : 'info'} size={20} />{t.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

/* Reveal on scroll -------------------------------------------------------- */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setSeen(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.12 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={cx(s.reveal, seen && s.in, className)} style={{ transitionDelay: `${delay}ms` }}>{children}</div>;
}

/* Count-up number --------------------------------------------------------- */
export function CountUp({ to, ms = 900 }: { to: number; ms?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setV(to); return; }
    const t0 = performance.now(); let raf = 0;
    const tick = (t: number) => { const p = Math.min(1, (t - t0) / ms); setV(Math.round(to * (1 - Math.pow(1 - p, 3)))); if (p < 1) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to, ms]);
  return <>{v}</>;
}
