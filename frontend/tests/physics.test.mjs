import test from 'node:test';
import assert from 'node:assert/strict';
import { projectile, snell, circuit, solid, SOLIDS } from '../src/lesson/sims/physics.ts';

const near = (a, b, tol = 1e-3) => assert.ok(Math.abs(a - b) <= tol, `${a} is not within ${tol} of ${b}`);

test('projectile: 20 m/s at 45 degrees on level ground', () => {
  const p = projectile({ v: 20, angle: 45, g: 9.8, h0: 0 });
  near(p.range, 40.816, 0.01); near(p.maxHeight, 10.204, 0.01); near(p.time, 2.886, 0.01);
  assert.equal(p.points.length > 10, true);
  near(p.points[0].x, 0); near(p.points.at(-1).y, 0, 1e-6);          // lands exactly on the ground
});

test('projectile: 45 degrees gives the longest range, and launching from a height adds to it', () => {
  const r = (a) => projectile({ v: 20, angle: a, g: 9.8, h0: 0 }).range;
  assert.ok(r(45) > r(30) && r(45) > r(60) && r(45) > r(15));
  near(r(30), r(60), 1e-6);                                            // complementary angles reach the same distance
  assert.ok(projectile({ v: 20, angle: 45, g: 9.8, h0: 10 }).range > r(45));
});

test('projectile: straight up goes nowhere sideways, and gravity scales the flight', () => {
  const up = projectile({ v: 10, angle: 90, g: 10, h0: 0 });
  near(up.range, 0, 1e-6); near(up.maxHeight, 5); near(up.time, 2);
  assert.ok(projectile({ v: 20, angle: 45, g: 1.62, h0: 0 }).range > 5 * projectile({ v: 20, angle: 45, g: 9.8, h0: 0 }).range);   // the Moon
});

test('projectile: bad inputs cannot produce NaN', () => {
  for (const bad of [{ v: -5, angle: 45, g: 9.8, h0: 0 }, { v: 10, angle: 45, g: 0, h0: 0 }, { v: NaN, angle: 45, g: 9.8, h0: 0 }]) {
    const p = projectile(bad);
    assert.ok(Number.isFinite(p.range) && Number.isFinite(p.time) && Number.isFinite(p.maxHeight));
  }
});

test('snell: air to glass at 30 degrees bends toward the normal', () => {
  const s = snell({ n1: 1, n2: 1.5, angle: 30 });
  near(s.refracted, 19.471, 0.01); assert.equal(s.critical, null); assert.equal(s.tir, false);
  assert.ok(s.reflectance > 0 && s.reflectance < 0.1);               // a little light always reflects
});

test('snell: glass to air has a critical angle and total internal reflection beyond it', () => {
  const below = snell({ n1: 1.5, n2: 1, angle: 40 });
  near(below.critical, 41.81, 0.01); assert.equal(below.tir, false); assert.ok(below.refracted > 40);
  const above = snell({ n1: 1.5, n2: 1, angle: 50 });
  assert.equal(above.tir, true); assert.equal(above.refracted, null); near(above.reflectance, 1);
});

test('snell: straight on does not bend, and equal media do not bend', () => {
  near(snell({ n1: 1, n2: 1.33, angle: 0 }).refracted, 0, 1e-9);
  near(snell({ n1: 1.33, n2: 1.33, angle: 37 }).refracted, 37, 1e-9);
  near(snell({ n1: 1, n2: 1.5, angle: 0 }).reflectance, 0.04, 1e-3);   // the textbook 4 % at normal incidence
});

test('circuit: series resistors share the current and the voltage splits', () => {
  const c = circuit({ volts: 6, r1: 2, r2: 4, mode: 'series' });
  near(c.total, 6); near(c.current, 1); near(c.branches[0].v, 2); near(c.branches[1].v, 4); near(c.branches[0].i, 1); near(c.power, 6);
  near(c.branches[0].v + c.branches[1].v, 6);
});

test('circuit: parallel resistors share the voltage and the current splits', () => {
  const c = circuit({ volts: 6, r1: 3, r2: 6, mode: 'parallel' });
  near(c.total, 2); near(c.current, 3); near(c.branches[0].i, 2); near(c.branches[1].i, 1); near(c.branches[0].v, 6); near(c.power, 18);
  near(c.branches[0].i + c.branches[1].i, c.current);
  assert.ok(c.total < Math.min(3, 6));                                 // always less than the smallest resistor
});

test('circuit: zero or negative resistance is held at a safe minimum, not infinity', () => {
  const c = circuit({ volts: 6, r1: 0, r2: -3, mode: 'parallel' });
  assert.ok(Number.isFinite(c.current) && Number.isFinite(c.total) && c.total > 0);
});

test('solids: volume and surface area match the formulas', () => {
  const sphere = solid('sphere', { r: 3 });
  near(sphere.volume, 113.097, 0.01); near(sphere.surface, 113.097, 0.01);
  const cone = solid('cone', { r: 3, h: 4 });
  near(cone.slant, 5); near(cone.volume, 37.699, 0.01); near(cone.surface, 75.398, 0.01);
  const cyl = solid('cylinder', { r: 2, h: 5 });
  near(cyl.volume, 62.832, 0.01); near(cyl.surface, 87.965, 0.01);
  const cuboid = solid('cuboid', { l: 4, w: 3, h: 2 });
  near(cuboid.volume, 24); near(cuboid.surface, 52); near(solid('cube', { a: 3 }).volume, 27); near(solid('cube', { a: 3 }).surface, 54);
});

test('solids: every solid declares its controls, and nonsense sizes are clamped', () => {
  for (const k of Object.keys(SOLIDS)) assert.ok(SOLIDS[k].params.length >= 1 && SOLIDS[k].label);
  const s = solid('sphere', { r: -4 });
  assert.ok(s.volume > 0 && Number.isFinite(s.surface));
  assert.throws(() => solid('torus', {}), /Unknown solid/);
});
