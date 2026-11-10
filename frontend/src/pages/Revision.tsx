import { useState } from 'react';
import { api } from '../api/client';
import { clearApiCache, useApi } from '../api/useApi';
import type { Revision } from '../api/types';
import { Button, Card, EmptyState, Skeleton, useToast } from '../ui/kit';
import s from './pages.module.css';

export default function RevisionPage() {
  const { data, error, loading, reload } = useApi<Revision>('/revision');
  const toast = useToast();
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const [busy, setBusy] = useState(false);

  if (loading && !data) return <Skeleton h={260} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load revision" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;

  if (data.due.length === 0) return <Card><EmptyState icon="check" title="Nothing to revise right now" text="When a topic becomes secure, ZENITH brings it back after a day, then a few days, then weeks, just before you would forget it." action={<Button to="/practice" variant="brand">Practise instead</Button>} /></Card>;
  if (data.cards.length === 0) return <Card><EmptyState icon="layers" title="Topics are due, but no cards yet" text={`${data.due.map((d) => d.title).join(', ')} are due. Reviewed flashcards are not available for them yet, so practise questions instead.`} action={<Button to="/practice?review=1" variant="brand">Practise due topics</Button>} /></Card>;

  const card = data.cards[i];
  if (!card) return <Card><EmptyState icon="trophy" title="Revision done" text="Nice. These topics will come back at the right time." action={<Button to="/home" variant="brand">Back to Home</Button>} /></Card>;

  async function rate(remembered: boolean) {
    setBusy(true);
    try { await api(`/revision/cards/${card.id}/review`, { method: 'POST', body: { remembered } }); clearApiCache(); setFlip(false); setI(i + 1); }
    catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.q}>
      <div className={s.between}><h1 className={s.title}>Revision</h1><span className="muted">Card {i + 1} of {data.cards.length}</span></div>
      <button className={s.flash} onClick={() => setFlip(!flip)} aria-label={flip ? 'Show the question' : 'Show the answer'}>
        <span className="eyebrow">{flip ? 'Answer' : 'Question'}</span><span className={s.flashText}>{flip ? card.back : card.front}</span><span className="hand">tap to {flip ? 'go back' : 'flip'}</span>
      </button>
      {flip && <div className={s.row}><Button variant="brand" loading={busy} icon="check" onClick={() => void rate(true)}>I remembered</Button><Button variant="ghost" loading={busy} icon="refresh" onClick={() => void rate(false)}>Show again tomorrow</Button></div>}
    </div>
  );
}
