import test from 'node:test';
import assert from 'node:assert/strict';
import { pickNext, markSeen } from '../src/offline/localPractice.ts';

const items = [
  { id: 'c', difficulty: 'challenge', lessonId: 'l1' }, { id: 'a', difficulty: 'intro', lessonId: 'l1' },
  { id: 'b', difficulty: 'standard', lessonId: 'l2' }, { id: 'd', difficulty: 'intro', lessonId: 'l2' },
];

test('offline practice starts with untried easy questions and climbs', () => {
  const order = [];
  let seen = {};
  for (let t = 1; t <= 4; t++) { const n = pickNext(items, seen); order.push(n.id); seen = markSeen(seen, n.id, t); }
  assert.deepEqual(order, ['a', 'd', 'b', 'c']);
});

test('once everything was tried, the one tried longest ago comes back first', () => {
  let seen = {};
  for (const [i, id] of ['a', 'b', 'c', 'd'].entries()) seen = markSeen(seen, id, 10 + i);
  assert.equal(pickNext(items, seen).id, 'a');
  assert.equal(pickNext(items, markSeen(seen, 'a', 99)).id, 'b');
});

test('excluded questions are skipped and an empty pool gives nothing', () => {
  assert.equal(pickNext(items, {}, ['a', 'd']).id, 'b');
  assert.equal(pickNext([], {}), null);
  assert.equal(pickNext(items, {}, ['a', 'b', 'c', 'd']), null);
});
