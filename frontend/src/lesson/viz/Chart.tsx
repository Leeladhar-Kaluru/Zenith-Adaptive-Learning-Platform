import { useState } from 'react';
import { useApi } from '../../api/useApi';
import { Skeleton } from '../../ui/kit';
import s from '../sims/sims.module.css';

interface Dataset { id: string; fields: string[]; rows: Array<Record<string, number | string>>; credit: { text: string; url: string; licence: string } }

const compact = (n: number) => (Math.abs(n) >= 1e9 ? `${(n / 1e9).toFixed(2)} billion` : Math.abs(n) >= 1e6 ? `${(n / 1e6).toFixed(1)} million` : Math.abs(n) >= 1e3 ? `${(n / 1e3).toFixed(1)} thousand` : String(Math.round(n * 100) / 100));
const W = 320, H = 200, PAD = { l: 44, r: 12, t: 12, b: 28 };

/** A real dataset drawn as a line or bar chart. Tap or use the arrow keys to read a value; the numbers are also in a table. */
export function Chart({ dataset, x, y, chart = 'line', task }: { dataset: string; x: string; y: string; chart?: string; task?: string }) {
  const { data, error, loading } = useApi<Dataset>(`/datasets/${dataset}`);
  const [at, setAt] = useState<number | null>(null);
  if (loading && !data) return <figure className={s.sim}><Skeleton h={220} r={16} /></figure>;
  if (error || !data) return <figure className={s.sim}><p className="muted">This chart could not be loaded.</p></figure>;
  const pts = data.rows.map((r) => ({ x: Number(r[x]), y: Number(r[y]), label: String(r[x]) })).filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (!pts.length) return <figure className={s.sim}><p className="muted">There is no data to show.</p></figure>;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = chart === 'bar' ? 0 : Math.min(...ys), y1 = Math.max(...ys);
  const sx = (v: number) => PAD.l + (x1 === x0 ? 0.5 : (v - x0) / (x1 - x0)) * (W - PAD.l - PAD.r);
  const sy = (v: number) => H - PAD.b - (y1 === y0 ? 0.5 : (v - y0) / (y1 - y0)) * (H - PAD.t - PAD.b);
  const sel = at === null ? null : pts[at];
  const move = (d: number) => setAt((i) => Math.max(0, Math.min(pts.length - 1, (i ?? 0) + d)));
  const bw = Math.max(3, ((W - PAD.l - PAD.r) / pts.length) * 0.7);
  return (
    <figure className={s.sim} aria-label={`Chart of ${y} by ${x}`}>
      <figcaption className={s.head}><b>Real data</b></figcaption>
      {task && <p className={s.task}>{task}</p>}
      <div className={s.stage}>
        <svg viewBox={`0 0 ${W} ${H}`} className={s.plot} tabIndex={0} role="img" aria-label={`${chart} chart of ${y} by ${x}, from ${compact(y0)} to ${compact(y1)}. Use the left and right arrow keys to read values.`}
          onKeyDown={(e) => { if (e.key === 'ArrowRight') { e.preventDefault(); move(1); } if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); } }}>
          <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} className={s.axis} /><line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} className={s.axis} />
          <text x={PAD.l - 4} y={PAD.t + 8} textAnchor="end" fontSize="9" fill="currentColor">{compact(y1)}</text>
          <text x={PAD.l - 4} y={H - PAD.b} textAnchor="end" fontSize="9" fill="currentColor">{compact(y0)}</text>
          <text x={PAD.l} y={H - 8} fontSize="9" fill="currentColor">{String(x0)}</text><text x={W - PAD.r} y={H - 8} textAnchor="end" fontSize="9" fill="currentColor">{String(x1)}</text>
          {chart === 'bar'
            ? pts.map((p, i) => <rect key={i} x={sx(p.x) - bw / 2} y={sy(p.y)} width={bw} height={Math.max(1, H - PAD.b - sy(p.y))} className={i === at ? s.win : s.curve} style={{ fill: i === at ? 'var(--ok)' : 'var(--brand)' }} onClick={() => setAt(i)} />)
            : <><polyline fill="none" className={s.curve} points={pts.map((p) => `${sx(p.x)},${sy(p.y)}`).join(' ')} />
              {pts.map((p, i) => <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={i === at ? 5 : 3} className={s.dot} onClick={() => setAt(i)} />)}</>}
        </svg>
      </div>
      <output className={s.readout} aria-live="polite">{sel ? `${sel.label}: ${compact(sel.y)}` : 'Tap a point or use the arrow keys to read a value.'}</output>
      <details><summary className="sm muted">See the numbers</summary>
        <table style={{ width: '100%', fontSize: '.85rem', marginTop: 8 }}><thead><tr><th align="left">{x}</th><th align="right">{y}</th></tr></thead>
          <tbody>{pts.map((p, i) => <tr key={i}><td>{p.label}</td><td align="right">{compact(p.y)}</td></tr>)}</tbody></table></details>
      <p className="sm muted">Source: <a href={data.credit.url} target="_blank" rel="noopener noreferrer">{data.credit.text}</a></p>
    </figure>
  );
}
