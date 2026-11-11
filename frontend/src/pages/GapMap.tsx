import { useApi } from '../api/useApi';
import type { Gaps } from '../api/types';
import { Icon } from '../icons/Icon';
import { Button, Card, Chip, EmptyState, Skeleton } from '../ui/kit';
import g from './gapmap.module.css';

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** One topic on a 0-100% line: coloured zones, the range your real level probably sits in, and your current estimate. */
function Range({ title, p, lo, hi }: { title: string; p: number; lo: number; hi: number }) {
  return (
    <div className={g.range} role="img" aria-label={`${title}: estimate ${pct(p)}, likely range ${pct(lo)} to ${pct(hi)}`}>
      <div className={g.zones}><i className={g.zGap} /><i className={g.zMid} /><i className={g.zOk} /></div>
      <span className={g.whisker} style={{ left: `${lo * 100}%`, width: `${Math.max(1, (hi - lo) * 100)}%` }} />
      <span className={g.dot} style={{ left: `${p * 100}%` }} />
      <div className={g.ticks} aria-hidden="true"><span>0</span><span>40</span><span>60</span><span>100%</span></div>
    </div>
  );
}

export function GapMap() {
  const { data, error, loading, reload } = useApi<Gaps>('/progress/gaps');
  if (loading && !data) return <Skeleton h={180} r={16} />;
  if (error && !data) return <EmptyState icon="wifiOff" title="Could not load your gap map" text={error.message} action={<Button onClick={reload} icon="refresh">Try again</Button>} />;
  if (!data) return null;
  const { gaps, summary, repairPath } = data;
  const titleOf = new Map(gaps.map((x) => [x.conceptId, x.title]));
  return (
    <section aria-labelledby="gap-h">
      <h2 id="gap-h" style={{ marginBottom: 6 }}>Where you are lacking</h2>
      <p className="muted sm" style={{ marginBottom: 12 }}>Worked out from {data.evidence} of your real answers. The bar shows your estimate; the thick line is the range your true level probably falls in. More answers make it narrower.</p>
      <div className={g.chips}>
        <Chip tone="ok">{summary.secure} secure</Chip><Chip tone="hi">{summary.learning} still learning</Chip><Chip tone="gap">{summary.gaps} to fix</Chip><Chip tone="soft">{summary.unmeasured} not measured yet</Chip>
      </div>
      {gaps.length === 0 ? (
        <Card><EmptyState icon={data.evidence ? 'check' : 'target'} title={data.evidence ? 'No gaps found' : 'Not enough answers yet'}
          text={data.evidence ? 'Nothing is clearly weak right now. Keep going: harder questions will find the edge of what you know.' : 'Answer a few questions in a lesson or in Practice. ZENITH needs at least two answers on a topic before it calls anything a gap.'}
          action={<Button to="/practice" variant="brand">Practise</Button>} /></Card>
      ) : (
        <>
          {repairPath.length > 1 && (
            <Card flat className={g.path}><strong>Fix in this order</strong>
              <ol>{repairPath.map((id, i) => <li key={id}><span>{i + 1}</span>{titleOf.get(id) ?? id}</li>)}</ol>
              <p className="sm muted">Earlier topics come first, because later ones build on them.</p></Card>
          )}
          <div className={g.list}>
            {gaps.map((x, i) => (
              <Card key={x.conceptId} flat>
                <div className={g.head}><div><strong>{x.title}</strong><div className="sm muted">Class {x.grade} · confidence {x.confidence}</div></div>
                  <div className={g.tags}>{i === 0 && <Chip tone="hi" icon="flag">Start here</Chip>}<Chip tone={x.band === 'gap_confirmed' ? 'gap' : 'hi'}>{x.band === 'gap_confirmed' ? 'Gap found' : 'Early signal'}</Chip></div></div>
                <Range title={x.title} p={x.p} lo={x.interval[0]} hi={x.interval[1]} />
                <p className="sm" style={{ marginTop: 6 }}>{x.reason}</p>
                {x.root && <p className={`sm ${g.root}`}><Icon name="compass" size={16} /> Fix <strong>{x.root.title}</strong> first. It is probably why this topic feels hard.</p>}
                <div className={g.actions}>
                  {x.actions.lesson && <Button to={x.actions.lesson} size="sm" variant="ghost" icon="book">{x.actions.startWith ? `Learn ${x.actions.startWith}` : 'Open the lesson'}</Button>}
                  <Button to={x.actions.practice} size="sm" variant="brand" icon="target">Practise this</Button>
                  <Button to={x.actions.test} size="sm" variant="ghost" icon="clipboard">Test this topic</Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
