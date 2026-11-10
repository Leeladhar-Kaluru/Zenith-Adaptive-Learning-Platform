import { useApi } from '../../api/useApi';
import type { ReviewQueueItem } from '../../api/types';
import { Icon } from '../../icons/Icon';
import { Button, Card, Chip, EmptyState, Reveal, Skeleton } from '../../ui/kit';
import s from '../pages.module.css';

const STATUS: Record<ReviewQueueItem['status'], { label: string; tone: 'hi' | 'ok' | 'gap' | 'soft' }> = {
  in_review: { label: 'Ready for review', tone: 'hi' }, changes_requested: { label: 'Changes requested', tone: 'gap' }, approved: { label: 'Approved', tone: 'ok' }, published: { label: 'Published', tone: 'ok' },
};

export default function Queue() {
  const { data, error, loading, reload } = useApi<ReviewQueueItem[]>('/review/queue');
  return (
    <div className={s.stack}>
      <div><h1 className={s.title}>Review queue</h1><p className={s.lead}>Nothing reaches students until a teacher approves it here. Automated checks run first; you make the final call.</p></div>
      {loading && !data && <div className={s.stack}>{[0, 1, 2].map((i) => <Skeleton key={i} h={86} r={16} />)}</div>}
      {error && !data && <EmptyState icon="wifiOff" title="Could not load the queue" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />}
      {data && data.length === 0 && <Card><EmptyState icon="check" title="All caught up" text="No lessons are waiting for review." /></Card>}
      <div className={s.stack}>
        {data?.map((r, i) => (
          <Reveal key={r.id} delay={i * 60}>
            <Card to={`/review/${r.id}`}>
              <div className={s.between}>
                <div><span className="eyebrow">{r.chapter}</span><h3>{r.title}</h3></div>
                <div className={s.row}>
                  {r.origin === 'ai_assisted' && <Chip icon="spark" tone="soft">AI-assisted draft</Chip>}
                  <Chip icon={r.gates.passed === r.gates.total ? 'check' : 'warn'} tone={r.gates.passed === r.gates.total ? 'ok' : 'hi'}>{r.gates.passed}/{r.gates.total} checks</Chip>
                  <Chip tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Chip>
                  <Icon name="chevR" size={20} />
                </div>
              </div>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
