import { useCallback, useEffect, useRef, useState } from 'react';
import type { RealtimeChannel } from '@supabase/realtime-js';
import { token } from '../api/client';

/**
 * Live class chat over a PRIVATE Supabase Realtime channel (class-chat:<id>). Only content-free pings ("something changed"),
 * typing and who-is-online travel here. Real messages always come from the API, which checks class membership.
 * If Realtime is not configured or the channel is refused, `connected` stays false and the chat polls instead.
 */
const URL_ = (import.meta.env.VITE_SUPABASE_URL ?? '').trim().replace(/\/+$/, '');
const KEY = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? '').trim();
const TYPING_MS = 3500;

export interface Live { connected: boolean; online: string[]; typing: string[]; ping: () => void; typingNow: () => void }

export function useClassRealtime(classId: string, nickname: string, onPing: () => void): Live {
  const [connected, setConnected] = useState(false);
  const [online, setOnline] = useState<string[]>([]);
  const [typing, setTyping] = useState<Record<string, number>>({});
  const [, tick] = useState(0);
  const chan = useRef<RealtimeChannel | null>(null);
  const cb = useRef(onPing);
  const lastTyping = useRef(0);
  cb.current = onPing;

  useEffect(() => {
    const jwt = token.get();
    if (!URL_ || !KEY || !jwt || jwt.startsWith('dev:')) return;
    let closed = false;
    let cleanup = () => {};
    void import('@supabase/realtime-js').then(({ RealtimeClient }) => {
      if (closed) return;
      const client = new RealtimeClient(`${URL_}/realtime/v1`, { params: { apikey: KEY } });
      void client.setAuth(jwt);
      const ch = client.channel(`class-chat:${classId}`, { config: { private: true, broadcast: { self: false }, presence: { key: crypto.randomUUID() } } });
      ch.on('broadcast', { event: 'changed' }, () => cb.current());
      ch.on('broadcast', { event: 'typing' }, ({ payload }: { payload?: { n?: string } }) => {
        const n = payload?.n;
        if (n) setTyping((t) => ({ ...t, [n]: Date.now() + TYPING_MS }));
      });
      ch.on('presence', { event: 'sync' }, () => {
        const st = ch.presenceState() as Record<string, Array<{ n?: string }>>;
        setOnline([...new Set(Object.values(st).flat().map((x) => x.n).filter((x): x is string => !!x))].sort());
      });
      ch.subscribe((status: string) => {
        if (closed) return;
        if (status === 'SUBSCRIBED') { chan.current = ch; setConnected(true); void ch.track({ n: nickname }); } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') { chan.current = null; setConnected(false); }
      });
      cleanup = () => { void client.removeChannel(ch); client.disconnect(); };
    }).catch(() => setConnected(false));
    return () => { closed = true; chan.current = null; setConnected(false); setOnline([]); cleanup(); };
  }, [classId, nickname]);

  // expire "is typing" labels
  useEffect(() => {
    const id = window.setInterval(() => tick((x) => x + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const ping = useCallback(() => { void chan.current?.send({ type: 'broadcast', event: 'changed', payload: {} }); }, []);
  const typingNow = useCallback(() => {
    const now = Date.now();
    if (now - lastTyping.current < 2000) return;
    lastTyping.current = now;
    void chan.current?.send({ type: 'broadcast', event: 'typing', payload: { n: nickname } });
  }, [nickname]);
  const now = Date.now();
  return { connected, online, typing: Object.entries(typing).filter(([n, until]) => until > now && n !== nickname).map(([n]) => n), ping, typingNow };
}
