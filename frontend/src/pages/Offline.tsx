import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listPacks, removePack, type OfflinePackRow } from '../offline/db';
import { Icon } from '../icons/Icon';
import { Button, Card, EmptyState, Reveal, useToast } from '../ui/kit';
import s from './pages.module.css';

const kb = (b: number) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

export default function Offline() {
  const [packs, setPacks] = useState<OfflinePackRow[] | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const toast = useToast();
  const load = () => void listPacks().then(setPacks);
  useEffect(() => {
    load();
    const on = () => setOnline(true), off = () => setOnline(false);
    addEventListener('online', on); addEventListener('offline', off);
    return () => { removeEventListener('online', on); removeEventListener('offline', off); };
  }, []);

  return (
    <div className={s.stack}>
      <div className={s.between}>
        <div><h1 className={s.title}>Offline lessons</h1><p className={s.lead}>Chapters you saved work without internet. Your answers are kept safely and sent when you are back online.</p></div>
        <span className="chip" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', padding: '5px 12px', border: '2px solid var(--ink)', borderRadius: 999, fontWeight: 800, background: online ? 'var(--ok-soft)' : 'var(--retry-soft)' }}><Icon name={online ? 'check' : 'wifiOff'} size={16} />{online ? 'Online' : 'Offline'}</span>
      </div>
      {packs && packs.length === 0 && <Card><EmptyState icon="download" title="Nothing saved yet" text="Open a chapter and choose Save for offline to study on a shared phone or with little data." action={<Button to="/learn" variant="brand" iconRight="arrowR">Browse chapters</Button>} /></Card>}
      <div className={s.grid}>
        {packs?.map((p, i) => (
          <Reveal key={p.chapterSlug} delay={i * 60}><Card>
            <div className={s.between}><h3>{p.title}</h3><button aria-label={`Remove ${p.title}`} onClick={async () => { await removePack(p.chapterSlug); toast('Removed from this device', 'ok'); load(); }}><Icon name="trash" size={20} /></button></div>
            <p className="muted sm">{p.lessons.length} lessons · {kb(p.bytes)} · saved {new Date(p.savedAt).toLocaleDateString()}</p>
            <div style={{ marginTop: 14 }}><Button to={`/lesson/${p.lessons[0]?.id}`} variant="ghost" size="sm" icon="book">Open</Button> <Link to={`/learn/${p.chapterSlug}`} className="sm muted" style={{ marginLeft: 10, textDecoration: 'underline' }}>Chapter page</Link></div>
          </Card></Reveal>
        ))}
      </div>
    </div>
  );
}
