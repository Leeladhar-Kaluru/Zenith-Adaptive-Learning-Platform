import { useRef, useState } from 'react';
import { api, API_BASE } from '../api/client';
import { uploadFile } from '../api/upload';
import type { ClassResourceItem } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, useToast } from '../ui/kit';
import c from './classes.module.css';

const MAX = 4 * 1024 * 1024;
const ACCEPT = 'application/pdf,image/png,image/jpeg,image/gif,image/webp,.docx,.xlsx,.pptx';
const size = (n: number) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const kindLabel = (t: string) => (t === 'application/pdf' ? 'PDF' : t.startsWith('image/') ? 'Picture' : t.includes('word') ? 'Word' : t.includes('sheet') ? 'Excel' : t.includes('presentation') ? 'PowerPoint' : 'File');
const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };

export function ClassResources({ classId, items, isTeacher, onChanged }: { classId: string; items: ClassResourceItem[]; isTeacher: boolean; onChanged: () => void }) {
  const toast = useToast();
  const base = `/classes/${classId}/resources`;
  const [mode, setMode] = useState<'file' | 'link'>('file');
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const ctl = useRef<AbortController | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const reset = () => { setTitle(''); setNote(''); setUrl(''); setFile(null); if (fileRef.current) fileRef.current.value = ''; };
  async function add() {
    setBusy(true);
    try {
      if (mode === 'link') await api(`${base}/link`, { method: 'POST', body: { title, url, note } });
      else if (file) {
        ctl.current = new AbortController();
        setProgress(0);
        await uploadFile(`${API_BASE}${base}/upload?${new URLSearchParams({ name: file.name, title, note })}`, file, setProgress, ctl.current.signal);
      }
      toast('Shared with the class', 'ok'); reset(); onChanged();
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); setProgress(null); }
  }
  async function open(r: ClassResourceItem) {
    try { const j = await api<{ url: string }>(`${base}/${r.id}/file`); window.open(j.url, '_blank', 'noopener'); } catch (e) { toast((e as Error).message, 'err'); }
  }
  async function remove(id: string) {
    try { await api(`${base}/${id}`, { method: 'DELETE' }); toast('Removed', 'ok'); setConfirming(null); onChanged(); } catch (e) { toast((e as Error).message, 'err'); }
  }
  const pick = (f?: File) => {
    if (f && f.size > MAX) { toast('That file is too big. The limit is 4 MB.', 'err'); if (fileRef.current) fileRef.current.value = ''; return; }
    setFile(f ?? null);
    if (f && !title.trim()) setTitle(f.name.replace(/\.[^.]+$/, '').slice(0, 120));
  };
  const ready = !!title.trim() && (mode === 'link' ? !!url.trim() : !!file);

  return (
    <section className={c.list} aria-label="Class resources">
      {isTeacher && (
        <Card flat>
          <div className={c.compose}>
            <h3>Share with the class</h3>
            <div className={c.actions} role="group" aria-label="What to share">
              <Button size="sm" variant={mode === 'file' ? 'brand' : 'ghost'} icon="upload" onClick={() => setMode('file')} aria-pressed={mode === 'file'}>A file</Button>
              <Button size="sm" variant={mode === 'link' ? 'brand' : 'ghost'} icon="share" onClick={() => setMode('link')} aria-pressed={mode === 'link'}>A link</Button>
            </div>
            {mode === 'file'
              ? <label className={c.fieldLbl}>File (PDF, picture, Word, Excel or PowerPoint, up to 4 MB)<input ref={fileRef} type="file" accept={ACCEPT} onChange={(e) => pick(e.target.files?.[0])} /></label>
              : <label className={c.fieldLbl}>Web address<input className={c.input} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" maxLength={500} inputMode="url" /></label>}
            <label className={c.fieldLbl}>Title<input className={c.input} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} /></label>
            <label className={c.fieldLbl}>Note for students (optional)<textarea className={c.input} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} /></label>
            {progress !== null && <div className={c.bar} role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Uploading"><span style={{ width: `${progress * 100}%` }} /><em>Uploading {Math.round(progress * 100)}%</em><button onClick={() => ctl.current?.abort()}>Cancel</button></div>}
            <div className={c.actions}><Button variant="brand" icon="check" loading={busy} disabled={!ready} onClick={() => void add()}>Share</Button></div>
          </div>
        </Card>
      )}
      {items.length === 0
        ? <Card><EmptyState icon="book" title="No resources yet" text={isTeacher ? 'Share notes, worksheets or links above.' : 'Notes, worksheets and links your teacher shares will appear here.'} /></Card>
        : items.map((r) => (
          <Card key={r.id} flat className={c.note}>
            <div className={c.noteHead}>
              <div><h3>{r.title}</h3>
                <div className={c.noteMeta}><Icon name={r.kind === 'link' ? 'share' : 'download'} size={14} /> {r.kind === 'link' ? `Link · ${host(r.url ?? '')}` : `${kindLabel(r.file?.type ?? '')} · ${size(r.file?.size ?? 0)}`} · {new Date(r.createdAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}</div></div>
              <Chip tone="soft">{r.kind === 'link' ? 'Link' : 'File'}</Chip>
            </div>
            {r.note && <p>{r.note}</p>}
            <div className={c.actions} style={{ marginTop: 12 }}>
              {r.kind === 'file'
                ? <Button size="sm" variant="brand" icon="download" onClick={() => void open(r)}>Open {r.file?.name}</Button>
                : <a className={c.linkBtn} href={r.url ?? '#'} target="_blank" rel="noopener noreferrer">Open link <span className="sm muted">(leaves ZENITH)</span></a>}
              {isTeacher && (confirming === r.id
                ? <><Button size="sm" variant="danger" onClick={() => void remove(r.id)}>Yes, remove</Button><Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>Keep</Button></>
                : <Button size="sm" variant="ghost" icon="trash" onClick={() => setConfirming(r.id)}>Remove</Button>)}
            </div>
          </Card>
        ))}
    </section>
  );
}
