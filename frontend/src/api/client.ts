const raw = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
export const API_BASE = raw ? (raw.endsWith('/api/v1') ? raw : `${raw}/api/v1`) : '/api/v1';
export const TOKEN_KEY = 'zenith_auth_token';

export class ApiError extends Error {
  constructor(public status: number, message: string, public retryable = false) {
    super(message);
  }
}

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

type Opts = { method?: string; body?: unknown; signal?: AbortSignal };

function message(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const t = token.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: opts.method ?? 'GET', headers, signal: opts.signal,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError(0, 'You appear to be offline, or ZENITH is waking up. Try again in a moment.', true);
  }
  if (res.status === 401 && t) token.clear();
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try { detail = (await res.json()).detail; } catch { /* not json */ }
    throw new ApiError(res.status, message(detail, 'Something went wrong.'), res.status >= 500 || res.status === 429);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
