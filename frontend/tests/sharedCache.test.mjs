import test from 'node:test';
import assert from 'node:assert/strict';
import { createSharedCache } from '../src/api/sharedCache.ts';

const later = () => { let resolve, reject; const p = new Promise((a, b) => { resolve = a; reject = b; }); return { p, resolve, reject }; };

test('concurrent callers share one request and the result is cached', async () => {
  let calls = 0;
  const c = createSharedCache(async (path) => { calls++; return `data:${path}`; });
  const [a, b] = await Promise.all([c.get('/today'), c.get('/today')]);
  assert.equal(a, 'data:/today'); assert.equal(b, 'data:/today'); assert.equal(calls, 1);
  assert.equal(c.peek('/today'), 'data:/today');
});

test('a response that arrives after clear() is not stored and later callers get a fresh request', async () => {
  const gates = [later(), later()]; let n = 0;
  const c = createSharedCache(() => gates[n++].p);
  const first = c.get('/today');
  c.clear();                                           // sign-out (or a write) while the request is on the way
  const second = c.get('/today');                      // must not join the old request
  assert.equal(n, 2);
  gates[0].resolve('OLD'); gates[1].resolve('NEW');
  assert.equal(await first, 'OLD'); assert.equal(await second, 'NEW');
  assert.equal(c.peek('/today'), 'NEW');
});

test('user B never receives user A\'s response after a sign-out and sign-in', async () => {
  const a = later(); let who = 'A';
  const c = createSharedCache((path) => (who === 'A' ? a.p : Promise.resolve(`B:${path}`)));
  const aReq = c.get('/today');
  c.clear(); who = 'B';
  assert.equal(await c.get('/today'), 'B:/today');
  a.resolve('A:/today');
  await aReq;
  assert.equal(c.peek('/today'), 'B:/today');          // A's late answer did not overwrite B's
});

test('invalidate() during a request keeps the stale answer out of the cache', async () => {
  const g = [later(), later()]; let n = 0;
  const c = createSharedCache(() => g[n++].p);
  const read = c.get('/chapter');                      // read starts
  c.invalidate('/chapter');                            // a write happens, then reload
  const fresh = c.get('/chapter');
  g[0].resolve('before-write'); g[1].resolve('after-write');
  await read; await fresh;
  assert.equal(c.peek('/chapter'), 'after-write');
});

test('a failed request is not cached and the next caller retries', async () => {
  let n = 0;
  const c = createSharedCache(async () => { n++; if (n === 1) throw new Error('offline'); return 'ok'; });
  await assert.rejects(c.get('/x'), /offline/);
  assert.equal(c.has('/x'), false); assert.equal(c.isLoading('/x'), false);
  assert.equal(await c.get('/x'), 'ok');
});

test('invalidateWhere drops matching cached values and in-flight requests only', async () => {
  const gate = later(); let n = 0;
  const c = createSharedCache((path) => (path === '/stats' ? gate.p : Promise.resolve(`v${++n}:${path}`)));
  await c.get('/progress/overview'); await c.get('/library/boards');
  const pending = c.get('/stats');
  c.invalidateWhere((p) => p.startsWith('/progress') || p === '/stats');
  assert.equal(c.has('/progress/overview'), false); assert.equal(c.has('/library/boards'), true); assert.equal(c.isLoading('/stats'), false);
  gate.resolve('late'); await pending;
  assert.equal(c.peek('/stats'), undefined);           // a response from before the change is not stored
});
