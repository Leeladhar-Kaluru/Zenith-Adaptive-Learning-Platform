import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { useApi } from '../../api/useApi';
import type { ReviewDetail } from '../../api/types';
import { useFx } from '../../fx/fx';
import { Icon } from '../../icons/Icon';
import { RenderBlock } from '../../lesson/Blocks';
import lessonCss from '../../lesson/lesson.module.css';
import { Button, Card, Chip, EmptyState, Sheet, Skeleton, useToast } from '../../ui/kit';
import s from '../pages.module.css';

export default function ReviewLesson() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const fx = useFx();
  const toast = useToast();
  const { data, error, loading, reload } = useApi<ReviewDetail>(`/review/lessons/${id}`);
  const [ack, setAck] = useState(false);
  const [changes, setChanges] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  if (loading && !data) return <div className={s.stack}><Skeleton h={44} w="50%" /><Skeleton h={300} r={16} /></div>;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not open this lesson" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const hard = data.gates.filter((g) => !g.passed && !g.manual);
  const manual = data.gates.filter((g) => !g.passed && g.manual);
  const canApprove = hard.length === 0 && (manual.length === 0 || ack);

  async function decide(decision: 'approve' | 'changes') {
    setBusy(true);
    try {
      await api(`/review/lessons/${id}`, { method: 'POST', body: { decision, comment: note || undefined, manualGatesConfirmed: ack } });
      if (decision === 'approve') fx.celebrate({ title: 'Approved', text: 'This lesson is now visible to students in its chapter.', icon: 'check', cta: 'Back to queue', onClose: () => nav('/review') });
      else { toast('Changes requested', 'ok'); nav('/review'); }
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.stack} data-subject={data.lesson.subject}>
      <Link to="/review" className="sm muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontWeight: 700 }}><Icon name="arrowL" size={16} />Review queue</Link>
      <div className={s.between}><div><span className="eyebrow">{data.chapter}</span><h1 className={s.title}>{data.title}</h1></div>{data.origin === 'ai_assisted' && <Chip icon="spark" tone="soft">AI-assisted draft</Chip>}</div>

      <div className={s.cols}>
        <Card>
          <h3>Automated checks</h3>
          <div style={{ marginTop: 8 }}>{data.gates.map((g) => (
            <div key={g.name} className={s.gate}><Icon name={g.passed ? 'check' : 'warn'} size={20} accent={g.passed ? 'var(--ok)' : 'var(--gap)'} /><div><div>{g.name}</div>{g.detail && <div className="sm muted" style={{ fontWeight: 500 }}>{g.detail}</div>}</div></div>
          ))}</div>
        </Card>
        <Card>
          <h3>AI reviewer notes</h3>
          <p className="sm muted" style={{ margin: '4px 0 10px' }}>These are flags only. They never approve anything.</p>
          {data.flags.map((f) => <div key={f.id} className={s.gate}><Icon name={f.severity === 'warn' ? 'warn' : 'info'} size={20} /><span style={{ fontWeight: 600 }}>{f.text}</span></div>)}
        </Card>
      </div>

      <section>
        <h2 style={{ marginBottom: 12 }}>Student view</h2>
        <Card style={{ padding: 28 }}>{data.lesson.blocks.map((b) => <div key={b.id} className={lessonCss.block}><RenderBlock b={b} /></div>)}</Card>
      </section>

      <Card flat style={{ position: 'sticky', bottom: 80, background: 'var(--surface)', boxShadow: 'var(--hard)' }}>
        {manual.length > 0 && (
          <label className="sm" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 12, fontWeight: 700 }}>
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} style={{ width: 22, height: 22, accentColor: 'var(--brand)' }} />
            <span>I checked this myself: {manual.map((m) => m.name.toLowerCase()).join(', ')}.</span>
          </label>
        )}
        {hard.length > 0 && <p className="sm" style={{ color: 'var(--gap)', fontWeight: 700, marginBottom: 12 }}>Fix the failed checks before this can be approved.</p>}
        <div className={s.row}>
          <Button variant="brand" icon="check" disabled={!canApprove} loading={busy} onClick={() => void decide('approve')}>Approve for students</Button>
          <Button variant="ghost" icon="edit" onClick={() => setChanges(true)}>Request changes</Button>
        </div>
      </Card>

      <Sheet open={changes} onClose={() => setChanges(false)} title="Request changes">
        <label className={s.field}>What should change?<textarea className={s.input} style={{ minHeight: 120, padding: 12 }} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Add a second worked example with a bigger jump." /></label>
        <div style={{ marginTop: 14 }}><Button variant="brand" loading={busy} disabled={note.trim().length < 3} onClick={() => void decide('changes')}>Send to author</Button></div>
      </Sheet>
    </div>
  );
}
