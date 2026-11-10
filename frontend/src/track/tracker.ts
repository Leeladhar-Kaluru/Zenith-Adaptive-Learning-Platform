import { API_BASE, token } from '../api/client';
import { db } from '../offline/db';

export type MoveKind = 'lesson_open' | 'section_view' | 'dwell' | 'hint_open' | 'answer_change' | 'sim_change' | 'sim_reset' | 'skip' | 'tutor_open';
export interface Move { clientEventId: string; kind: MoveKind; targetType: string; targetId: string; value: Record<string, unknown>; ms: number; occurredAt: string }

const FLUSH_MS = 5000;
const MAX_BUFFER = 150;
let buf: Move[] = [];
let timer: number | undefined;
let flushing = false;

/** Record one thing the student did. Batched, sent every few seconds, kept on the device if the network is down. */
export function track(kind: MoveKind, targetType: string, targetId: string, value: Record<string, unknown> = {}, ms = 0) {
  if (!token.get() || !targetId) return;
  buf.push({ clientEventId: crypto.randomUUID(), kind, targetType, targetId, value, ms: Math.max(0, Math.round(ms)), occurredAt: new Date().toISOString() });
  if (buf.length >= MAX_BUFFER) void flush();
  else if (timer === undefined) timer = window.setTimeout(() => { timer = undefined; void flush(); }, FLUSH_MS);
}

/** Per-key throttle so dragging a slider sends a few moves, not hundreds. */
const last = new Map<string, number>();
export function trackThrottled(key: string, everyMs: number, kind: MoveKind, targetType: string, targetId: string, value: Record<string, unknown> = {}) {
  const now = Date.now();
  if (now - (last.get(key) ?? 0) < everyMs) return;
  last.set(key, now);
  track(kind, targetType, targetId, value);
}

export async function flush(): Promise<void> {
  const t = token.get();
  if (flushing || !t) return;
  flushing = true;
  try {
    const stored = await db.moves.toArray().catch(() => [] as Move[]);
    const batch = [...stored, ...buf].slice(0, 200);
    if (!batch.length) return;
    const sent = new Set(batch.map((m) => m.clientEventId));
    buf = buf.filter((m) => !sent.has(m.clientEventId));
    const res = await fetch(`${API_BASE}/interactions/batch`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` }, body: JSON.stringify({ events: batch }), keepalive: true,
    }).catch(() => null);
    if (res && (res.ok || (res.status >= 400 && res.status < 500))) {
      // delivered, or rejected for a reason that will not change (no consent, not onboarded): do not retry forever
      await db.moves.bulkDelete([...sent]).catch(() => undefined);
    } else {
      await db.moves.bulkPut(batch).catch(() => undefined);        // offline or server error: keep for later
    }
  } finally { flushing = false; }
}

export function startTracker() {
  addEventListener('online', () => void flush());
  document.addEventListener('visibilitychange', () => document.visibilityState === 'hidden' && void flush());
  addEventListener('pagehide', () => void flush());
}
