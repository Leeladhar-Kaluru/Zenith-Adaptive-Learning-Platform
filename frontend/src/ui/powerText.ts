/** Lesson text is plain text, so powers are written 2^3, 10^-5 or 2^(n+1). These helpers find them so they can be shown as superscripts. */
const POWER = /\^(\([^)]*\)|[-−]?[A-Za-z0-9]+(?:\.[0-9]+)?)/g;
const inner = (g: string) => (g.startsWith('(') ? g.slice(1, -1) : g).replace(/^-/, '−');

/** "2^(-3) + x^2" -> ["2", {sup:"−3"}, " + x", {sup:"2"}] */
export function splitPowers(text: string): Array<string | { sup: string }> {
  const out: Array<string | { sup: string }> = [];
  let last = 0;
  for (const m of text.matchAll(POWER)) {
    if ((m.index ?? 0) > last) out.push(text.slice(last, m.index));
    out.push({ sup: inner(m[1]) });
    last = (m.index ?? 0) + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Same for text inside an inline SVG figure: labels cannot use <sup>, so a raised, smaller tspan is used. Only text between tags is touched. */
export function svgPowers(svg: string): string {
  if (!svg.includes('^')) return svg;
  return svg.replace(/>([^<>]*\^[^<>]*)</g, (_, t: string) => '>' + t.replace(POWER, (_m, g: string) => `<tspan baseline-shift="super" font-size="70%">${inner(g)}</tspan>`) + '<');
}
