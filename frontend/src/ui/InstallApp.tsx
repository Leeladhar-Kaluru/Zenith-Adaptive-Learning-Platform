import { useEffect, useState } from 'react';
import { Button, Card } from './kit';

interface BIPEvent extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }> }

const installed = () => matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

/** Install ZENITH as an app. Uses the browser's own install prompt where it exists, and tells iPhone users the two taps it needs. Hidden once installed. */
export function InstallApp({ compact }: { compact?: boolean }) {
  const [ev, setEv] = useState<BIPEvent | null>(null);
  const [done, setDone] = useState(installed());
  useEffect(() => {
    const on = (e: Event) => { e.preventDefault(); setEv(e as BIPEvent); };
    const ok = () => setDone(true);
    addEventListener('beforeinstallprompt', on); addEventListener('appinstalled', ok);
    return () => { removeEventListener('beforeinstallprompt', on); removeEventListener('appinstalled', ok); };
  }, []);
  if (done) return compact ? null : <Card flat><strong>ZENITH is installed on this device.</strong> <span className="muted sm">It opens like an app and works offline with the chapters you saved.</span></Card>;
  if (!ev && !isIos()) return compact ? null : <Card flat><strong>Install ZENITH</strong><p className="muted sm" style={{ margin: '6px 0 0' }}>In Chrome or Edge, open the browser menu and choose Install app (or Add to Home screen). Then ZENITH opens like an app and works offline with the chapters you saved.</p></Card>;
  return (
    <Card flat>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'space-between' }}>
        <div style={{ minWidth: 0 }}><strong>Install ZENITH on this device</strong>
          <div className="muted sm">{ev ? 'Opens like an app, and your saved chapters and practice work with no internet.' : 'On iPhone or iPad: tap Share, then Add to Home Screen. Your saved chapters then work with no internet.'}</div></div>
        {ev && <Button variant="brand" icon="download" onClick={() => { void ev.prompt(); void ev.userChoice.then((c) => { if (c.outcome === 'accepted') setDone(true); setEv(null); }); }}>Install</Button>}
      </div>
    </Card>
  );
}
