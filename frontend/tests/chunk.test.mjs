import test from 'node:test';
import assert from 'node:assert/strict';
import { BATCH, chunk } from '../src/offline/chunk.ts';

test('a long offline queue is split into batches the server accepts', () => {
  assert.ok(BATCH >= 1 && BATCH <= 100, 'the server rejects more than 100 events per request');
  const parts = chunk(Array.from({ length: 230 }, (_, i) => i));
  assert.deepEqual(parts.map((p) => p.length), [50, 50, 50, 50, 30]);
  assert.deepEqual(parts.flat(), Array.from({ length: 230 }, (_, i) => i));      // nothing lost, order kept
});

test('empty and small queues behave', () => {
  assert.deepEqual(chunk([]), []);
  assert.deepEqual(chunk([1, 2, 3]), [[1, 2, 3]]);
  assert.deepEqual(chunk([1, 2, 3, 4], 2), [[1, 2], [3, 4]]);
});
