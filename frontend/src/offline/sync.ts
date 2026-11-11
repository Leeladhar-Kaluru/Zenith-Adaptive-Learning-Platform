import { api } from '../api/client';
import { clearApiCache, emitProgress } from '../api/useApi';
import type { EvidenceRequest } from '../api/types';
import { chunk } from './chunk';
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
  let sent = 0;
  try {
    for (const part of chunk(await db.queue.toArray())) {
      const res = await api<{ results: Array<{ clientEventId: string; ok: boolean; status?: number }> }>('/evidence/batch', {
        method: 'POST', body: { events: part.map(({ queuedAt: _q, ...e }) => e) },
      });
      // Keep only events that failed for a reason that might pass later (network or server errors).
      const done = res.results.filter((r) => r.ok || (r.status && r.status < 500)).map((r) => r.clientEventId);
      await db.queue.bulkDelete(done);
      sent += done.length;
    }
  } catch {
    // offline, refused or a storage hiccup: what was already sent stays sent and the rest waits for the next try. A sync must never crash the app.
  } finally {
    flushing = false;
    if (sent) { clearApiCache(); emitProgress(); }
  }
  return sent;
}

export function startSync() {
  const run = () => void flush();
  addEventListener('online', run);
  addEventListener('focus', run);
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && run());
  run();
}
