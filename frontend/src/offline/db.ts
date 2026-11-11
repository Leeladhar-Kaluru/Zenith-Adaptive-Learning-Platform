import Dexie, { type Table } from 'dexie';
import type { EvidenceRequest, Lesson } from '../api/types';
import type { Move } from '../track/tracker';
import type { TutorReply } from '../api/types';

export interface OfflinePackRow { chapterSlug: string; title: string; savedAt: string; bytes: number; lessons: Lesson[] }
export interface QueuedEvidence extends EvidenceRequest { queuedAt: string }

/** A tutor question asked offline. `queued` waits to be sent; `answered` holds the reply; `failed` holds a reason to show. */
export interface Doubt { clientId: string; message: string; lessonId?: string; language: string; askedAt: string; status: 'queued' | 'answered' | 'failed'; reply?: TutorReply; error?: string }

class ZenithDB extends Dexie {
  packs!: Table<OfflinePackRow, string>;
  queue!: Table<QueuedEvidence, string>;
  moves!: Table<Move, string>;
  doubts!: Table<Doubt, string>;
  snapshots!: Table<{ key: string; data: unknown; savedAt: string }, string>;
  constructor() {
    super('ZenithDB');
    this.version(1).stores({ packs: 'chapterSlug', queue: 'clientEventId' });
    this.version(2).stores({ packs: 'chapterSlug', queue: 'clientEventId', moves: 'clientEventId' });
    this.version(3).stores({ packs: 'chapterSlug', queue: 'clientEventId', moves: 'clientEventId', doubts: 'clientId, status' });
    this.version(4).stores({ packs: 'chapterSlug', queue: 'clientEventId', moves: 'clientEventId', doubts: 'clientId, status', snapshots: 'key' });
  }
}
export const db = new ZenithDB();

export async function savePack(chapterSlug: string, title: string, lessons: Lesson[]) {
  const bytes = new Blob([JSON.stringify(lessons)]).size;
  await db.packs.put({ chapterSlug, title, savedAt: new Date().toISOString(), bytes, lessons });
}
export const listPacks = () => db.packs.toArray();
export const removePack = (slug: string) => db.packs.delete(slug);
export async function offlineLesson(id: string): Promise<Lesson | null> {
  for (const p of await db.packs.toArray()) { const l = p.lessons.find((x) => x.id === id); if (l) return l; }
  return null;
}
