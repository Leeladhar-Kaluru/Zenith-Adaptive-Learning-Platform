import { useState } from 'react';
import { useApi } from '../../api/useApi';
import { Icon } from '../../icons/Icon';
import { Skeleton } from '../../ui/kit';
import { track } from '../../track/tracker';
import s from '../sims/sims.module.css';

interface Geo { id: string; viewBox: [number, number]; features: Array<{ id: string; name: string; d: string }>; credit: { text: string; url: string; licence: string } }

/** A world map drawn from open map data. Tap or use the keyboard on a country to read its name; with a "find" task, tap the right one. */
export function Atlas({ dataset, find, task }: { dataset: string; find?: string; task?: string }) {
  const { data, error, loading } = useApi<Geo>(`/datasets/${dataset}`);
  const [picked, setPicked] = useState<string | null>(null);
  const [tries, setTries] = useState(0);
  const [done, setDone] = useState(false);
  if (loading && !data) return <figure className={s.sim}><Skeleton h={240} r={16} /></figure>;
  if (error || !data) return <figure className={s.sim}><p className="muted">This map could not be loaded.</p></figure>;
  const [vw, vh] = data.viewBox;
  const chosen = data.features.find((f) => f.id === picked);

  function choose(f: Geo['features'][number]) {
    setPicked(f.id);
    if (find) {
      setTries((t) => t + 1);
      const ok = f.name.toLowerCase() === find.toLowerCase();
      if (ok) setDone(true);
      track('sim_change', 'sim', `atlas:${dataset}`, { find, picked: f.name, correct: ok });
    }
  }

  return (
    <figure className={s.sim} aria-label="Interactive world map">
      <figcaption className={s.head}><span className={s.tag}><Icon name="compass" size={16} /> Explore</span><b>World map</b></figcaption>
      {(task || find) && <p className={`${s.task} ${done ? s.taskDone : ''}`} role="status">{done ? <><Icon name="check" size={18} accent="var(--ok)" /> Found it after {tries} {tries === 1 ? 'try' : 'tries'}.</> : <>{task ?? `Find ${find}.`}{find && <> Find: <b>{find}</b></>}</>}</p>}
      <div className={s.stage}>
        <svg viewBox={`0 0 ${vw} ${vh}`} className={s.plot} style={{ width: '100%', maxWidth: 640 }} role="group" aria-label="Countries of the world">
          <rect width={vw} height={vh} fill="var(--surface-2)" />
          {data.features.map((f) => (
            <path key={f.id + f.name} d={f.d} tabIndex={0} role="button" aria-label={f.name} aria-pressed={picked === f.id}
              fill={picked === f.id ? (find ? (done ? 'var(--ok)' : 'var(--gap)') : 'var(--brand)') : 'var(--surface)'} stroke="var(--ink-2)" strokeWidth=".6" vectorEffect="non-scaling-stroke"
              style={{ cursor: 'pointer' }} onClick={() => choose(f)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), choose(f))} />
          ))}
        </svg>
      </div>
      <output className={s.readout} aria-live="polite">{chosen ? chosen.name : 'Tap a country to see its name.'}</output>
      <p className="sm muted">Map data: <a href={data.credit.url} target="_blank" rel="noopener noreferrer">{data.credit.text}</a></p>
    </figure>
  );
}
