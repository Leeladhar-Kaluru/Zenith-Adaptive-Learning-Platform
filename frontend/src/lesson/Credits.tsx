import { Icon } from '../icons/Icon';
import s from './lesson.module.css';

export interface Credit { text: string; url: string; licence: string }

/** Who made the pictures and data used in a lesson, and under which licence. Shown whenever a lesson uses outside material. */
export function Credits({ credits }: { credits: Credit[] }) {
  if (!credits.length) return null;
  return (
    <section className={s.credits} aria-label="Credits">
      <h2><Icon name="info" size={18} /> Credits</h2>
      <ul>
        {credits.map((c) => (
          <li key={c.url}>{c.text} · <span className="muted">{c.licence}</span> · <a href={c.url} target="_blank" rel="noopener noreferrer">source</a></li>
        ))}
      </ul>
    </section>
  );
}
