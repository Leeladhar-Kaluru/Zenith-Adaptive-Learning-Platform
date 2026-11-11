/** Pure models behind the simulations. No DOM, no randomness: the same inputs always give the same numbers, so they can be tested. */

const finite = (v: number, fallback: number) => (Number.isFinite(v) ? v : fallback);
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, finite(v, lo)));
const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

/* ---- projectile motion: no air resistance ------------------------------------------------------- */
export interface Projectile { range: number; maxHeight: number; time: number; apexX: number; apexT: number; points: Array<{ x: number; y: number; t: number }> }

export function projectile({ v, angle, g, h0 }: { v: number; angle: number; g: number; h0: number }): Projectile {
  v = clamp(v, 0, 1000); angle = clamp(angle, 0, 90); g = clamp(g, 0.1, 50); h0 = clamp(h0, 0, 1000);
  const vx = v * Math.cos(rad(angle)), vy = v * Math.sin(rad(angle));
  const time = (vy + Math.sqrt(vy * vy + 2 * g * h0)) / g;           // positive root of h0 + vy t - g t^2 / 2 = 0
  const apexT = vy / g;
  const points = [];
  const n = 60;
  for (let i = 0; i <= n; i++) {
    const t = (time * i) / n;
    points.push({ t, x: vx * t, y: i === n ? 0 : Math.max(0, h0 + vy * t - 0.5 * g * t * t) });
  }
  return { range: vx * time, maxHeight: h0 + (vy * vy) / (2 * g), time, apexX: vx * apexT, apexT, points };
}

/* ---- refraction: Snell's law with Fresnel reflectance --------------------------------------------- */
export interface Refraction { refracted: number | null; critical: number | null; tir: boolean; reflectance: number }

export function snell({ n1, n2, angle }: { n1: number; n2: number; angle: number }): Refraction {
  n1 = clamp(n1, 1, 4); n2 = clamp(n2, 1, 4); angle = clamp(angle, 0, 89.9);
  const critical = n1 > n2 ? deg(Math.asin(n2 / n1)) : null;
  const s2 = (n1 / n2) * Math.sin(rad(angle));
  if (s2 >= 1) return { refracted: null, critical, tir: true, reflectance: 1 };
  const t1 = rad(angle), t2 = Math.asin(s2);
  const c1 = Math.cos(t1), c2 = Math.cos(t2);
  const rs = ((n1 * c1 - n2 * c2) / (n1 * c1 + n2 * c2)) ** 2;       // light polarised across the plane
  const rp = ((n1 * c2 - n2 * c1) / (n1 * c2 + n2 * c1)) ** 2;       // light polarised in the plane
  return { refracted: deg(t2), critical, tir: false, reflectance: (rs + rp) / 2 };
}

/* ---- two resistors, Ohm's law ----------------------------------------------------------------------- */
export interface Circuit { total: number; current: number; power: number; branches: Array<{ r: number; v: number; i: number; p: number }> }

export function circuit({ volts, r1, r2, mode }: { volts: number; r1: number; r2: number; mode: 'series' | 'parallel' }): Circuit {
  volts = clamp(volts, 0, 240); r1 = clamp(r1, 0.1, 1000); r2 = clamp(r2, 0.1, 1000);   // a real wire is never exactly zero ohms
  const total = mode === 'series' ? r1 + r2 : (r1 * r2) / (r1 + r2);
  const current = volts / total;
  const branch = (r: number) => {
    const i = mode === 'series' ? current : volts / r;
    const v = mode === 'series' ? current * r : volts;
    return { r, v, i, p: v * i };
  };
  return { total, current, power: volts * current, branches: [branch(r1), branch(r2)] };
}

/* ---- solids for the 3D viewer -------------------------------------------------------------------------- */
export interface Param { key: string; label: string; min: number; max: number; step: number; value: number }
export interface SolidDef { label: string; params: Param[] }
const p = (key: string, label: string, value: number, min = 1, max = 10, step = 0.5): Param => ({ key, label, value, min, max, step });

export const SOLIDS: Record<string, SolidDef> = {
  cube: { label: 'Cube', params: [p('a', 'Edge a', 3)] },
  cuboid: { label: 'Cuboid', params: [p('l', 'Length l', 4), p('w', 'Width w', 3), p('h', 'Height h', 2)] },
  cylinder: { label: 'Cylinder', params: [p('r', 'Radius r', 2), p('h', 'Height h', 5)] },
  cone: { label: 'Cone', params: [p('r', 'Radius r', 3), p('h', 'Height h', 4)] },
  sphere: { label: 'Sphere', params: [p('r', 'Radius r', 3)] },
};

export interface SolidResult { volume: number; surface: number; slant?: number; formulas: { volume: string; surface: string } }

export function solid(kind: string, v: Record<string, number>): SolidResult {
  const d = SOLIDS[kind];
  if (!d) throw new Error(`Unknown solid: ${kind}`);
  const x = (k: string) => clamp(v[k] ?? d.params.find((q) => q.key === k)!.value, 0.1, 100);
  const PI = Math.PI;
  switch (kind) {
    case 'cube': { const a = x('a'); return { volume: a ** 3, surface: 6 * a * a, formulas: { volume: 'V = a³', surface: 'S = 6a²' } }; }
    case 'cuboid': { const l = x('l'), w = x('w'), h = x('h'); return { volume: l * w * h, surface: 2 * (l * w + w * h + l * h), formulas: { volume: 'V = l × w × h', surface: 'S = 2(lw + wh + lh)' } }; }
    case 'cylinder': { const r = x('r'), h = x('h'); return { volume: PI * r * r * h, surface: 2 * PI * r * (r + h), formulas: { volume: 'V = πr²h', surface: 'S = 2πr(r + h)' } }; }
    case 'cone': { const r = x('r'), h = x('h'), l = Math.hypot(r, h); return { volume: (PI * r * r * h) / 3, surface: PI * r * (r + l), slant: l, formulas: { volume: 'V = ⅓πr²h', surface: 'S = πr(r + l),  l = √(r² + h²)' } }; }
    default: { const r = x('r'); return { volume: (4 / 3) * PI * r ** 3, surface: 4 * PI * r * r, formulas: { volume: 'V = ⁴⁄₃πr³', surface: 'S = 4πr²' } }; }
  }
}
