import test from 'node:test';
import assert from 'node:assert/strict';
import { splitPowers, svgPowers } from '../src/ui/powerText.ts';

test('powers become superscript parts, with brackets and signs handled', () => {
  assert.deepEqual(splitPowers('2^3 × 2^4'), ['2', { sup: '3' }, ' × 2', { sup: '4' }]);
  assert.deepEqual(splitPowers('a^(m+n) and 10^-5 and 10^(−2)'), ['a', { sup: 'm+n' }, ' and 10', { sup: '−5' }, ' and 10', { sup: '−2' }]);
  assert.deepEqual(splitPowers('no powers here'), ['no powers here']);
  assert.deepEqual(splitPowers('x^2.'), ['x', { sup: '2' }, '.']);       // a full stop after a power stays text
});

test('only text between svg tags is changed, never attributes or markup', () => {
  const svg = '<svg viewBox="0 0 10 10"><text x="1" y="2">2^3</text><path d="M0 0"/><text>10^(−2) m</text></svg>';
  const out = svgPowers(svg);
  assert.ok(out.includes('2<tspan baseline-shift="super" font-size="70%">3</tspan></text>'));
  assert.ok(out.includes('10<tspan baseline-shift="super" font-size="70%">−2</tspan> m'));
  assert.ok(out.includes('viewBox="0 0 10 10"') && out.includes('d="M0 0"'));
  assert.equal(svgPowers('<svg><text>plain</text></svg>'), '<svg><text>plain</text></svg>');
});
