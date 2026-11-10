import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, token, ApiError } from '../api/client';
import { clearApiCache } from '../api/useApi';
import type { Profile } from '../api/types';

type Theme = 'light' | 'dark' | 'system';
interface Auth {
  profile: Profile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<Profile>;
  signup: (input: { email: string; password: string; displayName: string; role: 'student' | 'teacher' }) => Promise<Profile>;
  logout: () => void;
  refresh: () => Promise<void>;
  setProfile: (p: Profile) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
}
const Ctx = createContext<Auth | null>(null);
export const useAuth = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth outside AuthProvider');
  return c;
};

const THEME_KEY = 'zenith_theme';
function applyTheme(t: Theme) {
  const r = document.documentElement;
  if (t === 'system') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', t);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(!!token.get());
  const [theme, setThemeState] = useState<Theme>(() => (localStorage.getItem(THEME_KEY) as Theme) || 'system');

  useEffect(() => applyTheme(theme), [theme]);
  const setTheme = useCallback((t: Theme) => { localStorage.setItem(THEME_KEY, t); setThemeState(t); }, []);

  const refresh = useCallback(async () => {
    if (!token.get()) { setProfile(null); setLoading(false); return; }
    try { setProfile(await api<Profile>('/profile')); }
    catch (e) { if (e instanceof ApiError && e.status === 401) token.clear(); setProfile(null); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const finish = useCallback((res: { token: string; profile: Profile }) => { token.set(res.token); clearApiCache(); setProfile(res.profile); return res.profile; }, []);
  const login = useCallback(async (email: string, password: string) => finish(await api('/auth/login', { method: 'POST', body: { email, password } })), [finish]);
  const signup = useCallback(async (input: { email: string; password: string; displayName: string; role: 'student' | 'teacher' }) => finish(await api('/auth/signup', { method: 'POST', body: input })), [finish]);
  const logout = useCallback(() => { token.clear(); clearApiCache(); setProfile(null); }, []);

  const value = useMemo(() => ({ profile, loading, login, signup, logout, refresh, setProfile, theme, setTheme }), [profile, loading, login, signup, logout, refresh, theme, setTheme]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
