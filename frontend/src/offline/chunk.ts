/** The server accepts at most 100 answers per sync request, so a long offline stretch is sent in smaller batches. */
export const BATCH = 50;

export function chunk<T>(items: T[], size: number = BATCH): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}
