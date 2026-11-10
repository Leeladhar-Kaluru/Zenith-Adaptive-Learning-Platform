import Dexie, { type Table } from 'dexie';
import type { EvidenceRequest, Lesson } from '../api/types';
import type { Move } from '../track/tracker';

export interface OfflinePackRow { chapterSlug: string; title: string; savedAt: string; bytes: number; lessons: Lesson[] }
export interface QueuedEvidence extends EvidenceRequest { queuedAt: string }

class ZenithDB extends Dexie {
  packs!: Table<OfflinePackRow, string>;
  queue!: Table<QueuedEvidence, string>;
  moves!: Table<Move, string>;
  constructor() {
    super('ZenithDB');
    this.version(1).stores({ packs: 'chapterSlug', queue: 'clientEventId' });
    this.version(2).stores({ packs: 'chapterSlug', queue: 'clientEventId', moves: 'clientEventId' });
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
