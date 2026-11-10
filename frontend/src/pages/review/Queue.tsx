import { useApi } from '../../api/useApi';
import type { Coverage, ReviewQueueItem } from '../../api/types';
import { Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton } from '../../ui/kit';
import s from '../pages.module.css';

const STATUS: Record<string, { label: string; tone: 'hi' | 'ok' | 'gap' | 'soft' }> = {
  draft: { label: 'Checks failed', tone: 'gap' }, in_review: { label: 'Ready for review', tone: 'hi' }, changes_requested: { label: 'Changes requested', tone: 'gap' }, approved: { label: 'Approved', tone: 'ok' },
};

export default function Queue() {
  const { data, error, loading, reload } = useApi<ReviewQueueItem[]>('/review/queue');
  const cov = useApi<Coverage[]>('/review/coverage');
  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Review queue</h1><p className={s.lead}>Nothing reaches students until a reviewer approves it here. Automated checks run first; you make the final call.</p></div>

      {cov.data && cov.data.length > 0 && (
        <section><h2 style={{ marginBottom: 12 }}>What is live</h2>
          <div className={s.grid}>{cov.data.map((c) => (
            <Card key={c.slug} flat><span className="eyebrow">Class {c.grade} · {c.subject}</span><h3>{c.title}</h3>
              <div className={s.between} style={{ marginTop: 8 }}><span className="sm muted">{c.published} of {c.lessons} lessons live</span><Chip tone={c.status === 'published' ? 'ok' : 'soft'}>{c.status === 'published' ? 'Open to students' : 'Not open'}</Chip></div></Card>
          ))}</div></section>
      )}

      <section><h2 style={{ marginBottom: 12 }}>Waiting for you</h2>
        {loading && !data && <div className={s.stack}>{[0, 1, 2].map((i) => <Skeleton key={i} h={86} r={16} />)}</div>}
        {error && !data && <EmptyState icon="wifiOff" title="Could not load the queue" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
        {data && data.length === 0 && <Card><EmptyState icon="check" title="All caught up" text="No lessons are waiting for review." /></Card>}
        <div className={s.stack}>{data?.map((r, i) => (
          <Reveal key={r.id} delay={i * 40}>
            <Card to={`/review/${r.id}`}>
              <div className={s.between}>
                <div><span className="eyebrow">{r.chapter} · version {r.version}</span><h3>{r.title}</h3></div>
                <div className={s.row}>
                  {r.origin === 'ai_assisted' && <Chip icon="spark" tone="soft">AI-assisted draft</Chip>}
                  <Chip icon={r.gates.passed === r.gates.total ? 'check' : 'warn'} tone={r.gates.passed === r.gates.total ? 'ok' : 'hi'}>{r.gates.passed}/{r.gates.total} checks</Chip>
                  <Chip tone={(STATUS[r.status] ?? STATUS.in_review).tone}>{(STATUS[r.status] ?? STATUS.in_review).label}</Chip>
                  <Icon name="chevR" size={20} />
                </div>
              </div>
            </Card>
          </Reveal>
        ))}</div></section>
    </div>
  );
}
