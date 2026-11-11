import { useState } from 'react';
import { useApi } from '../../api/useApi';
import { Icon } from '../../icons/Icon';
import { Skeleton } from '../../ui/kit';
import { track } from '../../track/tracker';
import s from '../sims/sims.module.css';

interface Feature { id: string; name: string; kind?: 'line' | 'point'; d?: string; x?: number; y?: number; info?: string }
interface Geo { id: string; viewBox: [number, number]; outline?: string; note?: string; label?: string; features: Feature[]; credit: { text: string; url: string; licence: string } }
type Layer = { key: string; label: string; geo: Geo };

/** A map drawn from open map data. Tap or use the keyboard on a place, river or peak to read its name; with a "find" task, tap the right one.
 *  Extra layers (rivers, peaks, mountain ranges) are drawn in exactly the same frame and can be switched on and off. */
export function Atlas({ dataset, overlays, find, task }: { dataset: string; overlays?: string; find?: string; task?: string }) {
  const ids = (overlays ?? '').split(',').map((x) => x.trim()).filter(Boolean).slice(0, 4);
  const base = useApi<Geo>(`/datasets/${dataset}`);
  const o0 = useApi<Geo>(ids[0] ? `/datasets/${ids[0]}` : null);
  const o1 = useApi<Geo>(ids[1] ? `/datasets/${ids[1]}` : null);
  const o2 = useApi<Geo>(ids[2] ? `/datasets/${ids[2]}` : null);
  const o3 = useApi<Geo>(ids[3] ? `/datasets/${ids[3]}` : null);
  const [picked, setPicked] = useState<{ layer: string; f: Feature } | null>(null);
  const [tries, setTries] = useState(0);
  const [done, setDone] = useState(false);
  const [hidden, setHidden] = useState<Record<string, boolean>>({});

  const data = base.data;
  if (base.loading && !data) return <figure className={s.sim}><Skeleton h={240} r={16} /></figure>;
  if (base.error || !data) return <figure className={s.sim}><p className="muted">This map could not be loaded.</p></figure>;
  const layers: Layer[] = [o0, o1, o2, o3].map((r, i) => ({ key: ids[i], geo: r.data })).filter((l): l is { key: string; geo: Geo } => !!l.key && !!l.geo)
    .map((l) => ({ key: l.key, label: l.geo.label || 'More', geo: l.geo }));
  const [vw, vh] = data.viewBox;
  const shown = layers.filter((l) => !hidden[l.key]);
  const areas = [{ key: 'base', geo: data, label: 'Map' }, ...shown.filter((l) => !l.geo.features.some((f) => f.kind))];
  const lines = shown.flatMap((l) => l.geo.features.filter((f) => f.kind === 'line').map((f) => ({ layer: l.key, f })));
  const points = shown.flatMap((l) => l.geo.features.filter((f) => f.kind === 'point').map((f) => ({ layer: l.key, f })));
  const sel = (layer: string, f: Feature) => picked?.layer === layer && picked.f.id === f.id;

  function choose(layer: string, f: Feature) {
    setPicked({ layer, f });
    if (find) {
      setTries((t) => t + 1);
      const ok = f.name.toLowerCase() === find.toLowerCase();
      if (ok) setDone(true);
      track('sim_change', 'sim', `atlas:${dataset}`, { find, picked: f.name, correct: ok });
    }
  }
  const press = (layer: string, f: Feature) => (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(layer, f); } };
  const hit = (layer: string, f: Feature) => (find && sel(layer, f) ? (done ? 'var(--ok)' : 'var(--gap)') : 'var(--brand)');

  return (
    <figure className={s.sim} aria-label="Interactive map">
      <figcaption className={s.head}><span className={s.tag}><Icon name="compass" size={16} /> Explore</span><b>Map</b></figcaption>
      {(task || find) && <p className={`${s.task} ${done ? s.taskDone : ''}`} role="status">{done ? <><Icon name="check" size={18} accent="var(--ok)" /> Found it after {tries} {tries === 1 ? 'try' : 'tries'}.</> : <>{task ?? `Find ${find}.`}{find && <> Find: <b>{find}</b></>}</>}</p>}
      {layers.length > 0 && (
        <div className={s.ops} role="group" aria-label="Map layers">
          {layers.map((l) => <button key={l.key} type="button" className={s.op} aria-pressed={!hidden[l.key]} onClick={() => setHidden((h) => ({ ...h, [l.key]: !h[l.key] }))}>{l.label}</button>)}
        </div>
      )}
      <div className={s.stage}>
        <svg viewBox={`0 0 ${vw} ${vh}`} className={s.plot} style={{ width: '100%', maxWidth: 640 }} role="group" aria-label="Map. Each shape, line or marker is something you can choose.">
          <rect width={vw} height={vh} fill="var(--surface-2)" />
          {data.outline && <path d={data.outline} fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.4" vectorEffect="non-scaling-stroke" aria-hidden="true" pointerEvents="none" />}
          {areas.map((a) => a.geo.features.map((f) => f.d && (
            <path key={`${a.key}${f.id}`} d={f.d} tabIndex={0} role="button" aria-label={f.name} aria-pressed={sel(a.key, f)}
              fill={sel(a.key, f) ? hit(a.key, f) : a.key === 'base' ? 'var(--surface)' : 'var(--brand-soft, #cfd6ff)'} fillOpacity={a.key === 'base' ? 1 : sel(a.key, f) ? 0.9 : 0.45}
              stroke="var(--ink-2)" strokeWidth={a.key === 'base' ? 0.6 : 1} strokeDasharray={a.key === 'base' ? undefined : '4 3'} vectorEffect="non-scaling-stroke"
              style={{ cursor: 'pointer' }} onClick={() => choose(a.key, f)} onKeyDown={press(a.key, f)} />
          )))}
          {lines.map(({ layer, f }) => (
            <g key={`${layer}${f.id}`} tabIndex={0} role="button" aria-label={f.name} aria-pressed={sel(layer, f)} onClick={() => choose(layer, f)} onKeyDown={press(layer, f)} style={{ cursor: 'pointer' }}>
              <path d={f.d} fill="none" stroke="transparent" strokeWidth="14" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
              <path d={f.d} fill="none" stroke={sel(layer, f) ? hit(layer, f) : '#2f7fd6'} strokeWidth={sel(layer, f) ? 3.5 : 2} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            </g>
          ))}
          {points.map(({ layer, f }) => (
            <g key={`${layer}${f.id}`} tabIndex={0} role="button" aria-label={f.info ? `${f.name}, ${f.info}` : f.name} aria-pressed={sel(layer, f)} onClick={() => choose(layer, f)} onKeyDown={press(layer, f)} style={{ cursor: 'pointer' }}>
              <circle cx={f.x} cy={f.y} r="14" fill="transparent" />
              <path d={`M${(f.x ?? 0) - 7},${(f.y ?? 0) + 6}L${f.x},${(f.y ?? 0) - 8}L${(f.x ?? 0) + 7},${(f.y ?? 0) + 6}Z`} fill={sel(layer, f) ? hit(layer, f) : '#8b5a2b'} stroke="var(--ink)" strokeWidth="1.5" />
              {sel(layer, f) && <text x={(f.x ?? 0) + 10} y={(f.y ?? 0) - 6} fontSize="13" fontWeight="700" fill="currentColor" stroke="var(--surface)" strokeWidth="3" paintOrder="stroke">{f.name}</text>}
            </g>
          ))}
        </svg>
      </div>
      <output className={s.readout} aria-live="polite">{picked ? <>{picked.f.name}{picked.f.info && <> · {picked.f.info}</>}</> : 'Tap a place to see its name.'}</output>
      {data.note && <p className="sm muted">{data.note}</p>}
      <p className="sm muted">Map data: <a href={data.credit.url} target="_blank" rel="noopener noreferrer">{data.credit.text}</a>
        {layers.some((l) => l.geo.features.some((f) => !f.kind)) && ' Mountain ranges and plateaus show approximate areas.'}</p>
    </figure>
  );
}
