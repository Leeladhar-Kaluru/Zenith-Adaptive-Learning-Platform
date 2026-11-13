import { useState } from 'react';
import { api, ApiError } from '../../api/client';
import { useApi } from '../../api/useApi';
import { Button, Card, Chip, EmptyState, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

interface Overview {
  aiEnabled: boolean; cronConfigured: boolean; queued: number;
  jobs: Array<{ id: string; kind: string; status: string; grade: number | null; subject: string | null; concept: string | null; topic: string | null; demand: number; error: string | null; attempts: number; maxAttempts: number; log: Array<{ at: string; level: string; msg: string }>; at: string }>;
  pages: Array<{ id: string; url: string; title: string | null; licence: string; credit: string; sections: number }>;
  drafts: Array<{ id: string; title: string; grade: number; subject: string; score: number; verdict: string; at: string }>;
}
interface Health { workerAlive: boolean; workerSleeping?: boolean; workers: Array<{ name: string; alive: boolean; lastSeen: string; stats: Record<string, number> }>; queue: Record<string, number>; oldestQueuedSeconds: number | null; failedLast24h: number }
interface Draft { id: string; title: string; scorecard: { checks: Array<{ name: string; passed: boolean; detail: string; hard: boolean }>; score: number; verdict: string }; yaml: string }

/** The reviewer's view of the content pipeline: what students asked for, source pages to approve, drafts with their scorecards. Nothing here publishes. */
export default function Pipeline() {
  const { data, error, loading, reload } = useApi<Overview>('/pipeline/overview');
  const health = useApi<Health>('/pipeline/health');
  const toast = useToast();
  const [busy, setBusy] = useState('');
  const [open, setOpen] = useState<Draft | null>(null);
  const act = async (key: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(key);
    try { await fn(); toast(ok, 'ok'); reload(); } catch (e) { toast(e instanceof ApiError ? e.message : 'That did not work.', 'err'); }
    setBusy('');
  };
  if (loading && !data) return <Skeleton h={240} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load the pipeline" text={error.message} action={<Button onClick={reload}>Try again</Button>} />;
  if (!data) return null;
  return (
    <div className={s.stack}>
      <div className={s.between}><div><h1 className={s.title}>Content pipeline</h1><p className={s.lead}>Students ask for lessons, the pipeline finds open-licence pages and drafts lessons, and a person approves everything before students see it.</p></div>
        <Button variant="brand" icon="refresh" loading={busy === 'run'} onClick={() => void act('run', () => api('/pipeline/run', { method: 'POST' }), 'Ran one batch')}>Run a batch now</Button></div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Chip tone={data.cronConfigured ? 'ok' : 'gap'}>{data.cronConfigured ? 'Scheduled daily run is on' : 'Scheduled run is off (CRON_SECRET not set)'}</Chip>
        <Chip tone={data.aiEnabled ? 'ok' : 'gap'}>{data.aiEnabled ? 'AI drafting is on' : 'AI drafting is off: pages are found but not drafted'}</Chip>
        <Chip tone={health.data?.workerAlive || health.data?.workerSleeping ? 'ok' : 'gap'}>{health.data ? (health.data.workerAlive ? `Background worker is running (${health.data.workers.filter((w) => w.alive).length})` : health.data.workerSleeping ? 'Worker is asleep (free plan) and wakes when there is work' : 'No background worker has reported in') : 'Checking the worker'}</Chip>
        {health.data && health.data.failedLast24h > 0 && <Chip tone="gap">{health.data.failedLast24h} failed in the last day</Chip>}
        {health.data?.oldestQueuedSeconds != null && <Chip tone="soft">Oldest waiting: {Math.max(1, Math.round(health.data.oldestQueuedSeconds / 60))} min</Chip>}
        <Chip tone="soft">{data.queued} request{data.queued === 1 ? '' : 's'} waiting</Chip>
      </div>

      <section><h2 style={{ marginBottom: 10 }}>Source pages to approve ({data.pages.length})</h2>
        {data.pages.length === 0 ? <Card><p className="muted">No pages are waiting.</p></Card> : data.pages.map((p) => (
          <Card key={p.id} flat style={{ marginBottom: 10 }}>
            <div className={s.between}><div style={{ minWidth: 0 }}><strong>{p.title || p.url}</strong><div className="sm muted" style={{ overflowWrap: 'anywhere' }}>{p.url}</div><div className="sm muted">{p.licence} · {p.sections} section{p.sections === 1 ? '' : 's'}</div><div className="sm" style={{ overflowWrap: 'anywhere' }}>{p.credit}</div></div>
              <Button size="sm" variant="brand" loading={busy === p.id} onClick={() => void act(p.id, () => api(`/pipeline/pages/${p.id}/approve`, { method: 'POST' }), 'Page approved')}>Approve page</Button></div>
          </Card>))}
      </section>

      <section><h2 style={{ marginBottom: 10 }}>Drafts waiting for review ({data.drafts.length})</h2>
        {data.drafts.length === 0 ? <Card><p className="muted">No drafts yet.</p></Card> : data.drafts.map((d) => (
          <Card key={d.id} flat style={{ marginBottom: 10 }}>
            <div className={s.between}><div><strong>{d.title}</strong><div className="sm muted">Class {d.grade} · {d.subject} · score {Math.round(d.score * 100)}%</div></div>
              <div className={s.row}><Chip tone={d.verdict === 'rejected' ? 'gap' : 'ok'}>{d.verdict === 'rejected' ? 'Rejected' : 'Ready for review'}</Chip>
                <Button size="sm" variant="ghost" onClick={() => void api<Draft>(`/pipeline/drafts/${d.id}`).then(setOpen)}>Scorecard</Button>
                <Button size="sm" variant="ghost" onClick={() => void act(`x${d.id}`, () => api(`/pipeline/drafts/${d.id}/dismiss`, { method: 'POST' }), 'Dismissed')}>Dismiss</Button></div></div>
          </Card>))}
        {open && <Card><div className={s.between}><h3>{open.title}</h3><Button size="sm" variant="ghost" onClick={() => setOpen(null)}>Close</Button></div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0' }}>{open.scorecard.checks.map((c) => <li key={c.name} style={{ marginBottom: 6 }}><span aria-label={c.passed ? 'passed' : 'failed'}>{c.passed ? '✓' : '✗'}</span> <strong>{c.name}</strong>{c.hard && <Chip tone="soft">must pass</Chip>}<div className="sm muted">{c.detail}</div></li>)}</ul>
          <p className="sm muted">To use this draft, copy the lesson file below into the content folder, finish what is marked TODO, and import it. It still goes through the gates and a named reviewer.</p>
          <textarea readOnly value={open.yaml} style={{ width: '100%', minHeight: 220, fontFamily: 'monospace', fontSize: 12 }} aria-label="Lesson file" />
          <Button size="sm" variant="brand" onClick={() => void act(`e${open.id}`, () => api(`/pipeline/drafts/${open.id}/export`, { method: 'POST' }), 'Marked as taken')}>I have taken this draft</Button></Card>}
      </section>

      <section><h2 style={{ marginBottom: 10 }}>Recent work</h2>
        {data.jobs.length === 0 ? <Card><p className="muted">No pipeline work yet.</p></Card> : data.jobs.map((j) => (
          <div key={j.id} className={s.between} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
            <span><strong>{j.kind}</strong> {j.grade ? `· Class ${j.grade}` : ''} {j.subject ?? ''} {j.concept ?? j.topic ?? ''}{j.error ? <span className="sm muted"> — {j.error}</span> : null}</span>
            <span className={s.row}><Chip tone={j.status === 'done' ? 'ok' : j.status === 'failed' || j.status === 'blocked' ? 'gap' : 'soft'}>{j.status}{j.kind === 'request' ? ` · ${j.demand} asked · try ${j.attempts}/${j.maxAttempts}` : ''}</Chip>
              {j.kind === 'request' && (j.status === 'failed' || j.status === 'blocked') && <Button size="sm" variant="ghost" loading={busy === `r${j.id}`} onClick={() => void act(`r${j.id}`, () => api(`/pipeline/jobs/${j.id}/retry`, { method: 'POST' }), 'Queued again')}>Retry</Button>}</span>
          </div>))}
      </section>
    </div>
  );
}
