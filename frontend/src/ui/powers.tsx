import { Fragment, type ReactNode } from 'react';
import { splitPowers } from './powerText';

export { svgPowers } from './powerText';

/** Show 2^3 as 2³ and 10^-5 as 10⁻⁵ (real superscripts) in any lesson text. */
export function pw(text?: string | null): ReactNode {
  if (!text || !text.includes('^')) return text ?? null;
  return <Fragment>{splitPowers(text).map((p, i) => (typeof p === 'string' ? p : <sup key={i}>{p.sup}</sup>))}</Fragment>;
}
