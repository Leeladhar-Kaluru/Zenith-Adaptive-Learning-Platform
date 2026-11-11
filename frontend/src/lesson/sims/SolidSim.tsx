import { useEffect, useMemo, useRef, useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { SOLIDS, solid } from './physics';
import s from './sims.module.css';

type Shape = keyof typeof SOLIDS;
const f = (n: number) => (Number.isFinite(n) ? n.toFixed(1) : '0');

function webgl(): boolean {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}
/** A device that is short on memory, or a student who asked for less data, gets the numbers and a button instead of a 3D scene. */
function lite(): boolean {
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  return (nav.deviceMemory !== undefined && nav.deviceMemory <= 1) || nav.connection?.saveData === true;
}

/** Real 3D, loaded only when this simulation appears: the solid is built from the sizes you set, so the picture and the formulas never disagree. */
function Viewer({ shape, values }: { shape: Shape; values: Record<string, number> }) {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<{ set: (shape: Shape, v: Record<string, number>) => void } | null>(null);
  const latest = useRef({ shape, values });
  latest.current = { shape, values };

  useEffect(() => {
    let dead = false, cleanup = () => {};
    void import('three').then((T) => {
      const el = host.current;
      if (dead || !el) return;
      const renderer = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      el.appendChild(renderer.domElement);
      renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;touch-action:none;border-radius:12px;cursor:grab';
      const scene = new T.Scene();
      const camera = new T.PerspectiveCamera(40, 1, 0.1, 200);
      scene.add(new T.AmbientLight(0xffffff, 0.75));
      const sun = new T.DirectionalLight(0xffffff, 1.4); sun.position.set(6, 10, 8); scene.add(sun);
      const group = new T.Group(); scene.add(group);
      group.rotation.set(0.5, -0.7, 0);
      let radius = 14, spin = true, dragging = false, lastX = 0, lastY = 0, frame = 0;
      const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduce) spin = false;

      const build = (kind: Shape, v: Record<string, number>) => {
        group.children.slice().forEach((c) => { group.remove(c); (c as import('three').Mesh).geometry?.dispose(); });
        const x = (k: string) => clamp(v[k] ?? SOLIDS[kind].params.find((q) => q.key === k)!.value, 0.5, 10);
        let g: import('three').BufferGeometry, top = 4;
        if (kind === 'cube') { g = new T.BoxGeometry(x('a'), x('a'), x('a')); top = x('a'); }
        else if (kind === 'cuboid') { g = new T.BoxGeometry(x('l'), x('h'), x('w')); top = Math.max(x('l'), x('h'), x('w')); }
        else if (kind === 'cylinder') { g = new T.CylinderGeometry(x('r'), x('r'), x('h'), 48); top = Math.max(2 * x('r'), x('h')); }
        else if (kind === 'cone') { g = new T.ConeGeometry(x('r'), x('h'), 48); top = Math.max(2 * x('r'), x('h')); }
        else { g = new T.SphereGeometry(x('r'), 48, 32); top = 2 * x('r'); }
        const mesh = new T.Mesh(g, new T.MeshStandardMaterial({ color: 0x6f7bff, roughness: 0.45, metalness: 0.05, transparent: true, opacity: 0.88 }));
        const edges = new T.LineSegments(new T.EdgesGeometry(g, 25), new T.LineBasicMaterial({ color: 0x14193a }));
        group.add(mesh, edges);
        radius = Math.max(8, top * 2.6);
      };
      const size = () => {
        const w = el.clientWidth || 300, h = el.clientHeight || 220;
        renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
      };
      const draw = () => { camera.position.set(0, radius * 0.25, radius); camera.lookAt(0, 0, 0); renderer.render(scene, camera); };
      const loop = () => { if (spin && !dragging) group.rotation.y += 0.006; draw(); frame = requestAnimationFrame(loop); };
      const down = (e: PointerEvent) => { dragging = true; lastX = e.clientX; lastY = e.clientY; renderer.domElement.setPointerCapture(e.pointerId); renderer.domElement.style.cursor = 'grabbing'; };
      const move = (e: PointerEvent) => {
        if (!dragging) return;
        group.rotation.y += (e.clientX - lastX) * 0.01; group.rotation.x = Math.max(-1.4, Math.min(1.4, group.rotation.x + (e.clientY - lastY) * 0.01));
        lastX = e.clientX; lastY = e.clientY; if (reduce) draw();
      };
      const up = () => { dragging = false; renderer.domElement.style.cursor = 'grab'; };
      const key = (e: KeyboardEvent) => {
        const k = e.key; if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(k)) return;
        e.preventDefault(); spin = false;
        group.rotation.y += k === 'ArrowLeft' ? -0.15 : k === 'ArrowRight' ? 0.15 : 0; group.rotation.x += k === 'ArrowUp' ? -0.15 : k === 'ArrowDown' ? 0.15 : 0; if (reduce) draw();
      };
      renderer.domElement.addEventListener('pointerdown', down); renderer.domElement.addEventListener('pointermove', move);
      renderer.domElement.addEventListener('pointerup', up); renderer.domElement.addEventListener('pointercancel', up);
      renderer.domElement.tabIndex = 0; renderer.domElement.addEventListener('keydown', key);
      const ro = new ResizeObserver(() => { size(); if (reduce) draw(); }); ro.observe(el);
      const visible = new IntersectionObserver(([en]) => { cancelAnimationFrame(frame); if (en.isIntersecting && !reduce) loop(); else if (en.isIntersecting) draw(); }, { threshold: 0.05 });
      visible.observe(el);

      api.current = { set: (k, v) => { build(k, v); if (reduce) draw(); } };
      build(latest.current.shape, latest.current.values); size(); if (reduce) draw();
      cleanup = () => {
        cancelAnimationFrame(frame); ro.disconnect(); visible.disconnect();
        group.children.forEach((c) => { const m = c as import('three').Mesh; m.geometry?.dispose(); (m.material as import('three').Material)?.dispose?.(); });
        renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove(); api.current = null;
      };
    }).catch(() => { /* leaves the empty box; the numbers still work */ });
    return () => { dead = true; cleanup(); };
  }, []);

  useEffect(() => { api.current?.set(shape, values); }, [shape, values]);
  return <div ref={host} className={s.stage3d} role="img" aria-label={`Interactive 3D ${SOLIDS[shape].label.toLowerCase()}. Drag to turn it, or use the arrow keys.`} />;
}

/** Build a solid, turn it round, and watch volume and surface area follow the formulas. */
export function SolidSim({ blockId, shape: s0 = 'cuboid', goal_volume, task = '', ...init }: { blockId: string; shape?: string; goal_volume?: number; task?: string } & Record<string, unknown>) {
  const simId = useSimId(blockId);
  const first = (Object.keys(SOLIDS).includes(s0) ? s0 : 'cuboid') as Shape;
  const defaults = (k: Shape) => Object.fromEntries(SOLIDS[k].params.map((q) => [q.key, clamp(Number(init[q.key] ?? q.value), q.min, q.max)]));
  const [shape, setShape] = useState<Shape>(first);
  const [vals, setVals] = useState<Record<string, number>>(() => defaults(first));
  const [can3d] = useState(() => !lite() && webgl());
  const [wants3d, setWants3d] = useState(() => !lite() && webgl());
  const r = useMemo(() => solid(shape, vals), [shape, vals]);
  const done = goal_volume !== undefined && Math.abs(r.volume - goal_volume) / goal_volume <= 0.03;
  const pick = (k: Shape) => { setShape(k); setVals(defaults(k)); };

  return (
    <SimFrame title="Solids in 3D" task={task} simId={simId} done={done} onReset={() => { setShape(first); setVals(defaults(first)); }}
      controls={<>
        <div className={s.ops} role="group" aria-label="Shape">{(Object.keys(SOLIDS) as Shape[]).map((k) => <button key={k} type="button" className={s.op} aria-pressed={shape === k} onClick={() => pick(k)}>{SOLIDS[k].label}</button>)}</div>
        {SOLIDS[shape].params.map((q) => <Slider key={q.key} id={q.key} label={q.label} value={vals[q.key] ?? q.value} min={q.min} max={q.max} step={q.step} simId={simId} onChange={(v) => setVals((o) => ({ ...o, [q.key]: v }))} />)}</>}
      readout={<>
        {SOLIDS[shape].label}: {SOLIDS[shape].params.map((q) => `${q.key} = ${vals[q.key] ?? q.value}`).join(', ')}{r.slant !== undefined ? `, slant l = ${f(r.slant)}` : ''}.{' '}
        {r.formulas.volume} = {f(r.volume)} cubic units. {r.formulas.surface} = {f(r.surface)} square units.
        {goal_volume !== undefined && <> Aim for a volume of about {goal_volume}.</>}
      </>}>
      {can3d && wants3d
        ? <Viewer shape={shape} values={vals} />
        : <div className={s.stage3d} style={{ display: 'grid', placeItems: 'center', textAlign: 'center', padding: 12 }}>
            <p style={{ margin: 0 }}>{can3d ? 'The 3D view is off to save data.' : 'The 3D view is not available on this device.'} The measurements below still update as you move the sliders.
              {can3d && <><br /><button type="button" className={s.op} onClick={() => setWants3d(true)} style={{ marginTop: 8 }}>Show 3D</button></>}</p>
          </div>}
    </SimFrame>
  );
}
