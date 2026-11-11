import { useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApi } from '../api/useApi';
import { Button, Card, Chip, useToast } from '../ui/kit';

interface Row { grade: number; subject: string; name: string; chapters: number; lessons: number; topics: number; topicsCovered: number; inReview: number; requested: number; youRequested?: boolean; missingTopics?: string[] }

/** What is really available for this class and subject, and a way to ask for more. The counts come straight from the database. */
export function Coverage({ subject, grade, name }: { subject: string; grade: number; name: string }) {
  const { data, reload } = useApi<{ rows: Row[] }>('/coverage');
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const row = data?.rows.find((r) => r.subject === subject && r.grade === grade);
  if (!row) return null;
  const ask = async () => {
    setBusy(true);
    try { await api('/coverage/request', { method: 'POST', body: { subject } }); toast(`Thanks. We will look for ${name} lessons for Class ${grade}.`, 'ok'); reload(); }
    catch (e) { toast(e instanceof ApiError ? e.message : 'Could not send your request.', 'err'); }
    setBusy(false);
  };
  const missing = row.topics - row.topicsCovered;
  return (
    <Card flat>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ minWidth: 0 }}>
          <strong>Class {grade} {name}: what is ready</strong>
          <div className="sm muted">{row.chapters} chapter{row.chapters === 1 ? '' : 's'} and {row.lessons} lesson{row.lessons === 1 ? '' : 's'} published · {row.topicsCovered} of {row.topics} topics have a lesson{row.inReview ? ` · ${row.inReview} lesson${row.inReview === 1 ? '' : 's'} being reviewed by a teacher` : ''}</div>
        </div>
        {missing > 0 && (row.youRequested ? <Chip icon="check" tone="ok">You asked for more{row.requested > 1 ? ` · ${row.requested} requests` : ''}</Chip>
          : <Button size="sm" variant="brand" icon="spark" loading={busy} onClick={() => void ask()}>Ask for more lessons</Button>)}
      </div>
      {missing > 0 && row.missingTopics && row.missingTopics.length > 0 && <p className="sm muted" style={{ marginTop: 8 }}>Still to come: {row.missingTopics.join(', ')}{missing > row.missingTopics.length ? ' and more' : ''}. New lessons are checked by a teacher before they appear.</p>}
    </Card>
  );
}
