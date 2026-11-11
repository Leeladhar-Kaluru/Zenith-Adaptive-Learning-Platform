import { useState } from 'react';
import { SimFrame, Slider, useSimId, clamp } from './SimFrame';
import { image } from './physics';
import s from './sims.module.css';

const ELEMENTS = [{ id: 'convex_lens', name: 'Convex lens', sign: 1, mirror: false }, { id: 'concave_lens', name: 'Concave lens', sign: -1, mirror: false },
  { id: 'concave_mirror', name: 'Concave mirror', sign: 1, mirror: true }, { id: 'convex_mirror', name: 'Convex mirror', sign: -1, mirror: true }] as const;

/** An object in front of a lens or mirror: where the image forms, how big it is, and whether it is real or virtual (1/v = 1/f − 1/u). */
export function OpticsSim({ blockId, element0 = 'convex_lens', f0 = 10, u0 = 25, goal, task = '' }: { blockId: string; element0?: string; f0?: number; u0?: number; goal?: string; task?: string }) {
  const simId = useSimId(blockId);
  const first = ELEMENTS.some((e) => e.id === element0) ? element0 : 'convex_lens';
  const [el, setEl] = useState<string>(first);
  const [f, setF] = useState(clamp(f0, 5, 20));
  const [u, setU] = useState(clamp(u0, 3, 60));
  const E = ELEMENTS.find((e) => e.id === el)!;
  const r = image({ f: E.sign * f, u });
  const done = r.v !== null && ((goal === 'real' && r.real) || (goal === 'virtual' && !r.real && E.sign > 0) || (goal === 'enlarged' && r.enlarged));
  const sc = 4, ax = 150, ay = 100;                       // 1 cm = 4 px; the element stands at x = 150
  const objX = ax - u * sc, imgX = r.v === null ? null : clamp(E.mirror ? ax - r.v * sc : ax + r.v * sc, 6, 294);   // far images are drawn at the edge; the readout gives the real distance
  const objH = 30, imgH = r.m === null ? 0 : clamp(r.m, -8, 8) * objH;
  return (
    <SimFrame title="Lens and mirror lab" task={task} simId={simId} done={done} onReset={() => { setEl(first); setF(clamp(f0, 5, 20)); setU(clamp(u0, 3, 60)); }}
      controls={<>
        <Slider id="u" label="Object distance (cm)" value={u} min={3} max={60} simId={simId} onChange={setU} />
        <Slider id="f" label="Focal length (cm)" value={f} min={5} max={20} simId={simId} onChange={setF} />
        <div className={s.ops} role="group" aria-label="Lens or mirror">{ELEMENTS.map((e) => <button key={e.id} type="button" className={s.op} aria-pressed={el === e.id} onClick={() => setEl(e.id)}>{e.name}</button>)}</div></>}
      readout={r.v === null ? <>The object is exactly at the focus. The rays come out parallel, so no image forms (it is at infinity).</> : <>
        {E.name}, f = {E.sign * f} cm, object {u} cm away. 1/v = 1/f − 1/u gives v = {r.v.toFixed(1)} cm: the image is <strong>{r.real ? 'real' : 'virtual'}, {r.upright ? 'upright' : 'upside down'}</strong> and {r.enlarged ? 'bigger than' : Math.abs(r.m!) === 1 ? 'the same size as' : 'smaller than'} the object (magnification {r.m!.toFixed(2)}).</>}>
      <svg viewBox="0 0 300 200" className={s.plot} role="img" aria-label={`An object ${u} centimetres from a ${E.name.toLowerCase()}. ${r.v === null ? 'No image forms.' : `The image is ${r.real ? 'real' : 'virtual'} and ${r.upright ? 'upright' : 'inverted'}.`}`}>
        <line x1="0" y1={ay} x2="300" y2={ay} stroke="currentColor" strokeWidth="1" opacity=".5" />
        <line x1={ax} y1="20" x2={ax} y2="180" stroke="currentColor" strokeWidth={E.mirror ? 5 : 3} />
        <text x={ax - 18} y="14" fontSize="10" fill="currentColor">{E.mirror ? 'mirror' : 'lens'}</text>
        <circle cx={ax - f * sc} cy={ay} r="2.5" fill="currentColor" /><circle cx={ax + f * sc} cy={ay} r="2.5" fill="currentColor" />
        <text x={ax - f * sc - 3} y={ay + 14} fontSize="9" fill="currentColor">F</text><text x={ax + f * sc - 3} y={ay + 14} fontSize="9" fill="currentColor">F</text>
        <line x1={objX} y1={ay} x2={objX} y2={ay - objH} stroke="var(--hi, #ffb800)" strokeWidth="4" strokeLinecap="round" />
        {imgX !== null && <line x1={imgX} y1={ay} x2={imgX} y2={ay - imgH} stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeDasharray={r.real ? undefined : '5 4'} />}
        <text x="6" y="192" fontSize="10" fill="currentColor">Yellow: object. Black: image ({r.v === null ? 'none' : r.real ? 'solid = real' : 'dashed = virtual'}).</text>
      </svg>
    </SimFrame>
  );
}
