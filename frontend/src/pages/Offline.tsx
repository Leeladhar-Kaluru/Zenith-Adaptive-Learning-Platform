import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import type { ChapterDetail, Lesson, Overview } from '../api/types';
import { savePack, listPacks, removePack, type OfflinePackRow } from '../offline/db';
import { InstallApp } from '../ui/InstallApp';
import { db } from '../offline/db';
import { flush, flushDoubts, pendingCount } from '../offline/sync';
import { Icon } from '../icons/Icon';
import { Button, Card, EmptyState, Reveal, useToast } from '../ui/kit';
import s from './pages.module.css';

const kb = (b: number) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

export default function Offline() {
  const [packs, setPacks] = useState<OfflinePackRow[] | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const toast = useToast();
  const [waiting, setWaiting] = useState(0);
  const [sending, setSending] = useState(false);
  const overview = useApi<Overview>(online ? '/progress/overview' : null);
  const [saving, setSaving] = useState('');
  const saveChapter = async (slug: string, title: string) => {
    setSaving(slug);
    try {
      const d = await api<ChapterDetail>(`/library/chapters/${slug}`);
      await savePack(slug, title, await Promise.all(d.lessons.map((l) => api<Lesson>(`/library/lessons/${l.id}`))));
      toast('Saved. Works without internet now.', 'ok'); load();
    } catch (e) { toast((e as Error).message, 'err'); }
    setSaving('');
  };
  const saved = new Set((packs ?? []).map((p) => p.chapterSlug));
  const suggested = (overview.data?.chapters ?? []).filter((c) => c.lessons > 0 && c.lessonsDone < c.lessons && !saved.has(c.slug)).sort((a, b) => a.lessonsDone / a.lessons - b.lessonsDone / b.lessons).slice(0, 3);
  const load = () => { void listPacks().then(setPacks); void Promise.all([pendingCount(), db.doubts.where('status').equals('queued').count()]).then(([a, d]) => setWaiting(a + d)); };
  const sendNow = async () => {
    setSending(true);
    const n = (await flush()) + (await flushDoubts());
    setSending(false); load();
    toast(n ? `Sent ${n} item${n === 1 ? '' : 's'}` : 'Nothing could be sent yet. Check your connection.', n ? 'ok' : 'err');
  };
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
      <InstallApp />
      {waiting > 0 && <Card flat><div className={s.between}><span><strong>{waiting} item{waiting === 1 ? '' : 's'} waiting</strong> <span className="muted sm">answers and questions saved on this device, not sent yet</span></span><Button size="sm" variant="brand" icon="upload" loading={sending} disabled={!online} onClick={() => void sendNow()}>Send now</Button></div></Card>}
      {packs && packs.length === 0 && <Card><EmptyState icon="download" title="Nothing saved yet" text="Open a chapter and choose Save for offline to study on a shared phone or with little data." action={<Button to="/learn" variant="brand" iconRight="arrowR">Browse chapters</Button>} /></Card>}
      {packs && packs.length > 0 && <div><Button to="/offline/practice" variant="brand" icon="target">Practise offline</Button> <span className="sm muted">Questions from your saved chapters. They are marked when you reconnect.</span></div>}
      {suggested.length > 0 && <section><h2 style={{ marginBottom: 10 }}>Suggested to save next</h2><p className="sm muted" style={{ marginBottom: 10 }}>Chapters you have started or not opened yet in your class, least finished first.</p><div className={s.grid}>{suggested.map((c) => <Card key={c.slug} flat><strong>{c.title}</strong><p className="sm muted" style={{ margin: '4px 0 10px' }}>{c.lessonsDone} of {c.lessons} lessons done</p><Button size="sm" variant="ghost" icon="download" loading={saving === c.slug} onClick={() => void saveChapter(c.slug, c.title)}>Save for offline</Button></Card>)}</div></section>}
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
