import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './client';
import { createSharedCache } from './sharedCache';

export interface Resource<T> { data: T | null; error: ApiError | null; loading: boolean; reload: () => void; setData: (v: T) => void }

const shared = createSharedCache((path) => api(path));

/** Start loading a page's data before the page asks for it (used while sign-in state is still being checked). */
export function prefetch(path: string): void {
  if (shared.has(path) || shared.isLoading(path)) return;
  shared.get(path).catch(() => undefined);
}

/** Fetch a GET endpoint with stale-while-revalidate caching; requests are shared, and answers that arrive after a reload or sign-out are never stored. */
export function useApi<T>(path: string | null): Resource<T> {
  const [data, setData] = useState<T | null>(() => (path && shared.peek<T>(path)) || null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(!!path && !shared.has(path));
  const tick = useRef(0);

  const load = useCallback(() => {
    if (!path) return () => {};
    let cancelled = false;
    setError(null);
    if (!shared.has(path)) setLoading(true);
    shared.get<T>(path)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof ApiError ? e : new ApiError(0, String(e?.message ?? e))); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [path]);

  useEffect(() => load(), [load, tick.current]); // eslint-disable-line react-hooks/exhaustive-deps
  const reload = useCallback(() => { if (path) shared.invalidate(path); tick.current++; load(); }, [load, path]);
  const set = useCallback((v: T) => { if (path) shared.set(path, v); setData(v); }, [path]);
  return { data, error, loading, reload, setData: set };
}

export const clearApiCache = () => shared.clear();

/** Screens whose numbers change when a student answers, finishes a lesson or submits a test. */
const PROGRESS_PATHS = /^\/(today|stats|progress|gamification|revision|assignments|mission|profile|quiz)\b/;

/** Call after anything that changes XP, streak, mastery or scores: cached progress screens are dropped and the header refreshes at once. */
export function emitProgress(): void {
  shared.invalidateWhere((p) => PROGRESS_PATHS.test(p));
  window.dispatchEvent(new Event('zenith:progress'));
}
