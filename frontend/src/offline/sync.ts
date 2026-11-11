import { api, ApiError } from '../api/client';
import { clearApiCache, emitProgress } from '../api/useApi';
import type { EvidenceRequest } from '../api/types';
import { db } from './db';

/** Save an answer on this device when the network is down. The server grades it later, so no result is shown offline. */
export async function queueEvidence(req: EvidenceRequest) {
  await db.queue.put({ ...req, occurredAt: req.occurredAt ?? new Date().toISOString(), queuedAt: new Date().toISOString() });
}

export const pendingCount = () => db.queue.count();

let flushing = false;
/** Send queued answers. Safe to call often: the server de-duplicates by clientEventId. */
export async function flush(): Promise<number> {
  if (flushing || !navigator.onLine) return 0;
  flushing = true;
  try {
    const items = await db.queue.toArray();
    if (!items.length) return 0;
    const res = await api<{ results: Array<{ clientEventId: string; ok: boolean; status?: number }> }>('/evidence/batch', {
      method: 'POST', body: { events: items.map(({ queuedAt: _q, ...e }) => e) },
    });
    // Keep only events that failed for a reason that might pass later (network or server errors).
    const done = res.results.filter((r) => r.ok || (r.status && r.status < 500)).map((r) => r.clientEventId);
    await db.queue.bulkDelete(done);
    if (done.length) { clearApiCache(); emitProgress(); }
    return done.length;
  } catch (e) {
    if (e instanceof ApiError && e.status === 0) return 0;
    return 0;
  } finally { flushing = false; }
}

export function startSync() {
  const run = () => void flush();
  addEventListener('online', run);
  addEventListener('focus', run);
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && run());
  run();
}
