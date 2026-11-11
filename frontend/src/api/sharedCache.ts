/**
 * A tiny request cache that shares one in-flight request per path.
 *
 * Every request carries a token. `invalidate(path)` and `clear()` drop the token, so a response that arrives
 * after a write, a reload or a sign-out is handed to whoever asked for it but is never stored, and is never
 * given to someone who asks later (for example the next person to sign in on the same device).
 */
export function createSharedCache(fetcher: (path: string) => Promise<unknown>) {
  const cache = new Map<string, unknown>();
  const inflight = new Map<string, Promise<unknown>>();
  const tokens = new Map<string, object>();

  function get<T>(path: string): Promise<T> {
    const running = inflight.get(path);
    if (running) return running as Promise<T>;
    const token = {};
    tokens.set(path, token);
    const p: Promise<unknown> = fetcher(path)
      .then((d) => { if (tokens.get(path) === token) cache.set(path, d); return d; })
      .finally(() => { if (inflight.get(path) === p) inflight.delete(path); });
    inflight.set(path, p);
    return p as Promise<T>;
  }

  return {
    get,
    peek: <T>(path: string) => cache.get(path) as T | undefined,
    has: (path: string) => cache.has(path),
    isLoading: (path: string) => inflight.has(path),
    set: (path: string, value: unknown) => { cache.set(path, value); },
    /** Forget one path: its cached value and any request still on the way. */
    invalidate: (path: string) => { cache.delete(path); inflight.delete(path); tokens.delete(path); },
    /** Forget everything (sign-in, sign-out, after a write). */
    clear: () => { cache.clear(); inflight.clear(); tokens.clear(); },
  };
}
