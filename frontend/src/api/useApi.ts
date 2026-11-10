import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './client';

export interface Resource<T> { data: T | null; error: ApiError | null; loading: boolean; reload: () => void; setData: (v: T) => void }

const cache = new Map<string, unknown>();
const inflight = new Map<string, Promise<unknown>>();

/** One network request per path at a time: components that ask for the same data share it. */
function fetchShared<T>(path: string): Promise<T> {
  const running = inflight.get(path);
  if (running) return running as Promise<T>;
  const p = api<T>(path).finally(() => inflight.delete(path));
  inflight.set(path, p);
  return p;
}

/** Start loading a page's data before the page asks for it (used while sign-in state is still being checked). */
export function prefetch(path: string): void {
  if (cache.has(path) || inflight.has(path)) return;
  fetchShared(path).then((d) => { cache.set(path, d); }).catch(() => undefined);
}

/** Fetch a GET endpoint with stale-while-revalidate caching and abort on unmount. */
export function useApi<T>(path: string | null): Resource<T> {
  const [data, setData] = useState<T | null>(() => (path && (cache.get(path) as T)) || null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(!!path && !cache.has(path));
  const tick = useRef(0);

  const load = useCallback(() => {
    if (!path) return () => {};
    let cancelled = false;
    setError(null);
    if (!cache.has(path)) setLoading(true);
    fetchShared<T>(path)
      .then((d) => { cache.set(path, d); if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof ApiError ? e : new ApiError(0, String(e?.message ?? e))); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [path]);

  useEffect(() => load(), [load, tick.current]); // eslint-disable-line react-hooks/exhaustive-deps
  const reload = useCallback(() => { if (path) cache.delete(path); tick.current++; load(); }, [load, path]);
  const set = useCallback((v: T) => { if (path) cache.set(path, v); setData(v); }, [path]);
  return { data, error, loading, reload, setData: set };
}

export const clearApiCache = () => cache.clear();
