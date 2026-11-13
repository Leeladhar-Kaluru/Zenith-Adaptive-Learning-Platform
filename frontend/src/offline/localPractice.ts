/** Offline practice from lessons saved on this device. Pure, so it can be tested: no network, no clock.
 *
 * Marks are given by the server after reconnecting (answers are never graded on the device), so nothing here depends on whether an answer was right.
 * Order: questions not yet tried on this device first, then the ones tried longest ago; inside each group easier before harder, so a student warms up and then
 * climbs. When the device syncs, the real engine updates the profile from these answers and the next online question adapts to them. */
export interface LocalItem { id: string; difficulty: 'intro' | 'standard' | 'challenge'; lessonId: string }
export type Seen = Record<string, { n: number; at: number }>;

const RANK = { intro: 0, standard: 1, challenge: 2 } as const;

export function pickNext<T extends LocalItem>(items: T[], seen: Seen, exclude: string[] = []): T | null {
  const pool = items.filter((i) => !exclude.includes(i.id));
  if (pool.length === 0) return null;
  const key = (i: T) => [seen[i.id]?.n ? 1 : 0, seen[i.id]?.at ?? 0, RANK[i.difficulty] ?? 1, i.id] as const;
  return [...pool].sort((a, b) => { const x = key(a), y = key(b); for (let k = 0; k < 4; k++) { if (x[k] < y[k]) return -1; if (x[k] > y[k]) return 1; } return 0; })[0];
}

export const markSeen = (seen: Seen, id: string, at: number): Seen => ({ ...seen, [id]: { n: (seen[id]?.n ?? 0) + 1, at } });
