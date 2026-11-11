import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import { Icon } from '../icons/Icon';
import s from './shell.module.css';

interface Item { id: string; kind: string; title: string; body: string; link: string | null; at: string; read: boolean }
interface Feed { unread: number; items: Item[] }

const ago = (iso: string) => { const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };

/** The bell: new lessons for your class, pipeline news for reviewers. Checks every 30 s while the tab is visible, and on focus and reconnect. */
export function NotificationBell() {
  const { data, reload } = useApi<Feed>('/notifications');
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  useEffect(() => {
    const go = () => { if (document.visibilityState === 'visible') reload(); };
    const id = setInterval(go, 30000);
    addEventListener('focus', go); addEventListener('online', go); document.addEventListener('visibilitychange', go);
    return () => { clearInterval(id); removeEventListener('focus', go); removeEventListener('online', go); document.removeEventListener('visibilitychange', go); };
  }, [reload]);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc); };
  }, [open]);
  const toggle = useCallback(() => {
    setOpen((o) => !o);
    if (!open && data && data.unread > 0) void api('/notifications/read', { method: 'POST', body: {} }).then(reload).catch(() => undefined);
  }, [open, data, reload]);
  const unread = data?.unread ?? 0;
  return (
    <div ref={box} style={{ position: 'relative' }}>
      <button className={s.iconBtn} onClick={toggle} aria-label={unread ? `Notifications, ${unread} new` : 'Notifications'} aria-expanded={open} aria-haspopup="true">
        <Icon name="bell" size={22} />
        {unread > 0 && <span style={{ position: 'absolute', top: 2, right: 2, minWidth: 18, height: 18, padding: '0 4px', borderRadius: 9, background: 'var(--gap, #d6455d)', color: '#fff', fontSize: 11, fontWeight: 800, display: 'grid', placeItems: 'center', border: '2px solid var(--surface)' }}>{unread > 9 ? '9+' : unread}</span>}
      </button>
      {open && (
        <div role="dialog" aria-label="Notifications" style={{ position: 'absolute', right: 0, top: 'calc(100% + 8px)', width: 'min(340px, 86vw)', maxHeight: '60vh', overflow: 'auto', zIndex: 40, background: 'var(--surface)', color: 'var(--ink)', border: '2px solid var(--ink)', borderRadius: 14, padding: 8, boxShadow: '4px 4px 0 var(--ink)' }}>
          {!data || data.items.length === 0 ? <p className="muted sm" style={{ padding: 12 }}>Nothing new. When a teacher publishes a lesson for your class, it shows up here.</p> : data.items.map((n) => (
            <button key={n.id} onClick={() => { setOpen(false); if (n.link) nav(n.link); }} style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 12px', border: 0, borderRadius: 10, background: n.read ? 'transparent' : 'var(--brand-soft)', color: 'inherit', cursor: n.link ? 'pointer' : 'default', font: 'inherit' }}>
              <strong style={{ display: 'block', overflowWrap: 'anywhere' }}>{n.title}</strong>
              {n.body && <span className="sm muted" style={{ display: 'block', overflowWrap: 'anywhere' }}>{n.body}</span>}
              <span className="sm muted">{ago(n.at)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
