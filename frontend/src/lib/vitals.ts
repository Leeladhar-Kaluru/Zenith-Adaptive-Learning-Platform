import { API_BASE } from '../api/client';

type Name = 'LCP' | 'INP' | 'CLS' | 'TTFB' | 'FCP';
const seen: Partial<Record<Name, number>> = {};

/** Measure how fast this page really felt, using the browser's own performance entries, and send it anonymously when the page is hidden. */
export function startVitals() {
  if (typeof PerformanceObserver === 'undefined') return;
  const watch = (type: string, fn: (e: PerformanceEntry) => void) => {
    try { new PerformanceObserver((l) => l.getEntries().forEach(fn)).observe({ type, buffered: true } as PerformanceObserverInit); } catch { /* not supported */ }
  };
  watch('largest-contentful-paint', (e) => { seen.LCP = e.startTime; });
  watch('paint', (e) => { if (e.name === 'first-contentful-paint') seen.FCP = e.startTime; });
  let cls = 0;
  watch('layout-shift', (e) => { const s = e as PerformanceEntry & { value: number; hadRecentInput: boolean }; if (!s.hadRecentInput) { cls += s.value; seen.CLS = cls * 1000; } });
  let worst = 0;
  watch('event', (e) => { const d = (e as PerformanceEntry & { interactionId?: number }).interactionId ? e.duration : 0; if (d > worst) { worst = d; seen.INP = d; } });
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
  if (nav) seen.TTFB = nav.responseStart;

  let sent = false;
  const flush = () => {
    if (sent || document.visibilityState !== 'hidden') return;
    sent = true;
    for (const [name, value] of Object.entries(seen)) {
      // CLS is stored x1000 so it fits the same numeric column as milliseconds
      const body = JSON.stringify({ name, value: Math.max(0, Math.round(value as number)), route: location.pathname });
      try { navigator.sendBeacon(`${API_BASE}/vitals`, new Blob([body], { type: 'application/json' })); } catch { /* ignore */ }
    }
  };
  document.addEventListener('visibilitychange', flush);
  addEventListener('pagehide', flush);
}
