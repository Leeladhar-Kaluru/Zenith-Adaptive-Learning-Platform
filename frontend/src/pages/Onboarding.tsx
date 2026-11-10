import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Avatar, AVATAR_IDS, Icon } from '../icons/Icon';
import { Button, Card, useToast } from '../ui/kit';
import type { Profile } from '../api/types';
import s from './pages.module.css';

const LANGS = [{ v: 'en', l: 'English' }, { v: 'hi', l: 'हिन्दी' }, { v: 'te', l: 'తెలుగు' }] as const;

export default function Onboarding() {
  const { profile, setProfile } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const teacher = profile?.role === 'teacher';
  const total = teacher ? 2 : 4;
  const [step, setStep] = useState(0);
  const [grade, setGrade] = useState<number | null>(null);
  const [lang, setLang] = useState<'en' | 'hi' | 'te'>('en');
  const [nick, setNick] = useState('');
  const [avatar, setAvatar] = useState('fox');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  const next = () => setStep((x) => x + 1);
  const back = () => setStep((x) => Math.max(0, x - 1));
  const steps = teacher ? ['name', 'done'] : ['class', 'language', 'name', 'join'];
  const cur = steps[step];

  async function finish() {
    setBusy(true);
    try {
      const p = await api<Profile>('/profile', { method: 'PUT', body: { grade, boardId: 'cbse', language: lang, nickname: nick.trim(), avatar, classCode: code.trim() || undefined, onboardingCompleted: true } });
      setProfile(p);
      nav(teacher ? '/teacher' : '/today', { replace: true });
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  const canNext = cur === 'class' ? grade !== null : cur === 'name' ? nick.trim().length >= 2 : true;

  return (
    <div className={s.authWrap}>
      <Card className={s.authCard} key={cur}>
        <div className={s.steps} aria-label={`Step ${step + 1} of ${total}`}>{Array.from({ length: total }, (_, i) => <i key={i} className={i <= step ? s.on : ''} />)}</div>

        {cur === 'class' && (<>
          <div><span className={s.tag}>Step 1</span><h1 style={{ fontSize: '1.9rem' }}>Which class are you in?</h1><p className="muted">We show lessons for your class and look back at earlier classes when you need a refresher.</p></div>
          <div className={s.pick}>{[6, 7, 8, 9, 10].map((g) => <button key={g} className={s.opt} aria-pressed={grade === g} onClick={() => setGrade(g)}>Class {g}</button>)}</div>
          <p className="sm muted"><Icon name="info" size={16} /> Board: CBSE. More boards are coming.</p>
        </>)}

        {cur === 'language' && (<>
          <div><span className={s.tag}>Step 2</span><h1 style={{ fontSize: '1.9rem' }}>Pick your language for explanations</h1><p className="muted">Lessons are written in English. Hindi and Telugu explanations are AI-translated and labelled.</p></div>
          <div className={s.pick}>{LANGS.map((l) => <button key={l.v} className={s.opt} aria-pressed={lang === l.v} onClick={() => setLang(l.v)} lang={l.v}>{l.l}</button>)}</div>
        </>)}

        {cur === 'name' && (<>
          <div><span className={s.tag}>{teacher ? 'Step 1' : 'Step 3'}</span><h1 style={{ fontSize: '1.9rem' }}>Choose a nickname and character</h1><p className="muted">Classmates see only your nickname and character, never your real name.</p></div>
          <label className={s.field}>Nickname
            <input className={s.input} value={nick} onChange={(e) => setNick(e.target.value)} maxLength={16} placeholder="e.g. Kiwi" autoFocus />
          </label>
          <div className={s.avatars} role="group" aria-label="Character">
            {AVATAR_IDS.map((a) => <button key={a} className={s.avBtn} aria-pressed={avatar === a} onClick={() => setAvatar(a)} aria-label={a}><Avatar id={a} size={52} /></button>)}
          </div>
        </>)}

        {cur === 'join' && (<>
          <div><span className={s.tag}>Step 4</span><h1 style={{ fontSize: '1.9rem' }}>Have a class code?</h1><p className="muted">Your teacher gives you a code like ZEN-4K7P. Skip this to learn on your own; you can join later in Settings.</p></div>
          <label className={s.field}>Class code (optional)
            <input className={s.input} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} maxLength={12} placeholder="ZEN-XXXX" />
          </label>
        </>)}

        {cur === 'done' && (<>
          <div><span className={s.tag}>All set</span><h1 style={{ fontSize: '1.9rem' }}>Ready to set up your class</h1><p className="muted">You can create a classroom, share its code, and review lessons before students see them.</p></div>
        </>)}

        <div className={s.between}>
          {step > 0 ? <Button variant="ghost" size="sm" icon="arrowL" onClick={back}>Back</Button> : <span />}
          {step < total - 1
            ? <Button variant="brand" iconRight="arrowR" disabled={!canNext} onClick={next}>Continue</Button>
            : <Button variant="brand" loading={busy} onClick={finish} iconRight="peak">Start climbing</Button>}
        </div>
      </Card>
    </div>
  );
}
