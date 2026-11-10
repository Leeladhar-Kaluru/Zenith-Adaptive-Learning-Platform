import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import type { Lesson } from '../api/types';
import AskPanel from '../ask/AskPanel';
import { useFx } from '../fx/fx';
import { Icon } from '../icons/Icon';
import { RenderBlock } from '../lesson/Blocks';
import s from '../lesson/lesson.module.css';
import { Button, Card, EmptyState, Sheet, Skeleton, useToast } from '../ui/kit';
import p from './pages.module.css';

export default function LessonPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const fx = useFx();
  const toast = useToast();
  const { data, error, loading, reload } = useApi<Lesson>(`/library/lessons/${id}`);
  const [ask, setAsk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [seen, setSeen] = useState(0);

  useEffect(() => { setSeen(0); }, [id]);
  useEffect(() => {
    if (!data) return;
    const els = Array.from(document.querySelectorAll('[data-blk]'));
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && setSeen((x) => Math.max(x, Number((e.target as HTMLElement).dataset.blk) + 1))), { threshold: 0.4 });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, [data]);

  const heads = useMemo(() => (data?.blocks ?? []).filter((b) => 'heading' in b && b.heading || b.kind === 'check' || b.kind === 'summary'), [data]);
  const remember = useMemo(() => data?.blocks.find((b) => b.kind === 'callout' && b.tone === 'remember') ?? null, [data]);

  if (loading && !data) return <div className={p.stack}><Skeleton h={14} w="40%" /><Skeleton h={50} w="70%" /><Skeleton h={160} r={16} /><Skeleton h={220} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not open this lesson" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;

  const pct = Math.min(100, Math.round((seen / Math.max(1, data.blocks.length)) * 100));

  async function finish() {
    if (!data) return;
    setBusy(true);
    try {
      await api('/progress', { method: 'POST', body: { lessonId: data.id } });
      const go = () => nav(data.nextId ? `/lesson/${data.nextId}` : `/learn/${data.chapterSlug}`);
      fx.celebrate({ title: data.nextId ? 'Lesson complete!' : 'Chapter complete!', text: data.nextId ? 'Nice work. Your next lesson is ready.' : 'You finished every lesson in this chapter.', icon: data.nextId ? 'star' : 'trophy', cta: data.nextId ? 'Next lesson' : 'Back to chapter', onClose: go });
      fx.xp(20);
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div data-subject={data.subject}>
      <div className={s.progressTop} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Lesson progress"><b style={{ width: `${pct}%` }} /></div>
      <div className={s.wrap}>
        <nav className={s.toc} aria-label="Chapter lessons">
          <Link to={`/learn/${data.chapterSlug}`} className="eyebrow">Chapter · {data.chapterTitle}</Link>
          <ol>{data.siblings.map((l) => <li key={l.id}><Link to={`/lesson/${l.id}`} aria-current={l.id === data.id ? 'step' : undefined}>{l.order} · {l.title}</Link></li>)}</ol>
        </nav>

        <article>
          {data.prereqGap && (
            <div className={p.prereq} style={{ marginBottom: 24 }}>
              <Icon name="compass" size={30} accent="var(--gap)" />
              <div style={{ flex: 1 }}><strong>Strengthen this first</strong><div className="sm">{data.prereqGap.title} (Class {data.prereqGap.grade}). We saw a gap here.</div></div>
              {data.prereqGap.lessonId && <Button to={`/lesson/${data.prereqGap.lessonId}`} size="sm" variant="ghost">5-minute refresher</Button>}
            </div>
          )}
          <header className={s.block}>
            <span className="eyebrow">{data.order} · {data.chapterTitle}</span>
            <h1 style={{ fontSize: 'clamp(2rem,5vw,3rem)', margin: '6px 0' }}>{data.title}</h1>
            <span className="muted sm"><Icon name="clock" size={16} /> {data.minutes} min</span>
          </header>
          {data.blocks.map((b, i) => <section key={b.id} className={s.block} data-blk={i} id={b.id}><RenderBlock b={b} /></section>)}
          <div className={s.notesBtn}><Button variant="ghost" icon="chat" onClick={() => setAsk(true)}>Ask ZENITH</Button></div>
        </article>

        <aside className={s.notes} aria-label="Notes">
          <Card className="sm"><span className="eyebrow">On this page</span>
            <ol style={{ listStyle: 'none', marginTop: 8, display: 'grid', gap: 6, fontWeight: 700, color: 'var(--ink-2)' }}>
              {heads.map((b) => <li key={b.id}><a href={`#${b.id}`}>{'heading' in b && b.heading ? b.heading : b.kind === 'check' ? 'Think first, then check' : 'Remember'}</a></li>)}
            </ol>
          </Card>
          {remember && remember.kind === 'callout' && <Card style={{ background: 'var(--hi)', color: 'var(--hi-ink)' }}><span className="hand" style={{ color: 'inherit' }}>remember</span><div className="sm" style={{ fontWeight: 700 }} dangerouslySetInnerHTML={{ __html: remember.html }} /></Card>}
          <Card><span className="eyebrow">Ask ZENITH</span><p className="sm muted">Stuck? Ask in English, Hindi or Telugu.</p><Button variant="ghost" size="sm" block onClick={() => setAsk(true)} icon="chat">Ask a question</Button></Card>
        </aside>
      </div>

      <div className={s.bar}>
        <Button variant="ghost" size="sm" icon="arrowL" disabled={!data.prevId} onClick={() => data.prevId && nav(`/lesson/${data.prevId}`)}>Previous</Button>
        <div className={s.dots} aria-hidden="true">{data.siblings.map((l) => <i key={l.id} className={l.order <= data.order ? s.on : ''} />)}</div>
        <Button size="sm" iconRight="arrowR" loading={busy} onClick={finish}>{data.nextId ? 'Finish & next' : 'Finish chapter'}</Button>
      </div>

      <Sheet open={ask} onClose={() => setAsk(false)} title="Ask ZENITH"><AskPanel lessonId={data.id} compact /></Sheet>
    </div>
  );
}
