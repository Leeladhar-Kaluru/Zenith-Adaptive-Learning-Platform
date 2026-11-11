import { api, ApiError } from '../api/client';
import type { TutorReply } from '../api/types';
import { clearApiCache, emitProgress } from '../api/useApi';
import type { EvidenceRequest } from '../api/types';
import { chunk } from './chunk';
import { db } from './db';

/** Save an answer on this device when the network is down. The server grades it later, so no result is shown offline. */
export async function queueEvidence(req: EvidenceRequest) {
  await db.queue.put({ ...req, occurredAt: req.occurredAt ?? new Date().toISOString(), queuedAt: new Date().toISOString() });
}

export const pendingCount = () => db.queue.count();

export const DOUBTS_EVENT = 'zenith-doubts';
/** Keep a tutor question on this device while offline. It is sent when the network is back; the same clientId makes a retry safe. */
export async function queueDoubt(message: string, language: string, lessonId?: string) {
  const d = { clientId: crypto.randomUUID(), message, language, lessonId, askedAt: new Date().toISOString(), status: 'queued' as const };
  await db.doubts.put(d);
  dispatchEvent(new Event(DOUBTS_EVENT));
  return d;
}

let sendingDoubts = false;
/** Ask every queued question, oldest first. A network or server error leaves it queued; a refusal (limit, consent) is kept as a reason. */
export async function flushDoubts(): Promise<number> {
  if (sendingDoubts || !navigator.onLine) return 0;
  sendingDoubts = true;
  let done = 0;
  try {
    for (const d of (await db.doubts.where('status').equals('queued').toArray()).sort((a, b) => a.askedAt.localeCompare(b.askedAt))) {
      try {
        const reply = await api<TutorReply>('/tutor/ask', { method: 'POST', body: { message: d.message, lessonId: d.lessonId, language: d.language, clientId: d.clientId } });
        await db.doubts.update(d.clientId, { status: 'answered', reply });
        done++;
      } catch (e) {
        if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
          await db.doubts.update(d.clientId, { status: 'failed', error: e.status === 429 ? 'You have asked a lot today. Try again tomorrow, or reread the lesson.' : 'ZENITH could not take this question. Ask it again.' });
        } else break;           // offline or server trouble: try the rest later
      }
    }
  } catch { /* storage hiccup: the queue stays as it is */ } finally {
    sendingDoubts = false;
    dispatchEvent(new Event(DOUBTS_EVENT));
  }
  return done;
}

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
  const run = () => { void flush(); void flushDoubts(); };
  addEventListener('online', run);
  addEventListener('focus', run);
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && run());
  run();
}
