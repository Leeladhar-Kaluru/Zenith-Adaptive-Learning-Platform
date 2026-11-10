import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import { useAuth } from '../context/AuthContext';
import { Avatar, AVATAR_IDS, Icon } from '../icons/Icon';
import { Button, Card, useToast } from '../ui/kit';
import type { Boards, Lang, Profile } from '../api/types';
import s from './pages.module.css';

const LANGS: Array<{ v: Lang; l: string }> = [{ v: 'en', l: 'English' }, { v: 'hi', l: 'हिन्दी' }, { v: 'te', l: 'తెలుగు' }];
const GOALS = [{ v: 'concept_mastery', l: 'Understand concepts well' }, { v: 'board_exam_prep', l: 'Prepare for exams' }, { v: 'fill_gaps', l: 'Fix what I missed earlier' }, { v: 'fast_track', l: 'Move ahead faster' }, { v: 'homework_help', l: 'Get help with homework' }];

export default function Onboarding() {
  const { profile, setProfile } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const boards = useApi<Boards>('/library/boards');
  const teacher = profile?.role === 'teacher';
  const steps = teacher ? ['name'] : ['class', 'language', 'interests', 'name', 'join'];
  const [step, setStep] = useState(0);
  const [grade, setGrade] = useState<number | null>(null);
  const [board, setBoard] = useState<string | null>(null);
  const [lang, setLang] = useState<Lang>('en');
  const [subjects, setSubjects] = useState<string[]>([]);
  const [goals, setGoals] = useState<string[]>([]);
  const [nick, setNick] = useState('');
  const [avatar, setAvatar] = useState('fox');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const cur = steps[step];
  const toggle = (list: string[], v: string, set: (x: string[]) => void) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const bs = boards.data?.boards ?? [];
  const chosenBoard = board ?? (bs.length === 1 ? bs[0].id : null);
  const canNext = cur === 'class' ? grade !== null && !!chosenBoard : cur === 'name' ? nick.trim().length >= 2 : true;

  async function finish() {
    setBusy(true);
    try {
      let p = await api<Profile>('/profile', { method: 'PUT', body: { grade: teacher ? undefined : grade, boardId: chosenBoard ?? undefined, language: lang, subjects, goals, nickname: nick.trim(), avatar, onboardingCompleted: true } });
      if (code.trim()) {
        try { p = await api<Profile>('/profile', { method: 'PUT', body: { classCode: code.trim() } }); } catch (e) { toast(`${(e as Error).message} You can add it later in Settings.`, 'info'); }
      }
      setProfile(p);
      nav(teacher ? '/teacher' : '/home', { replace: true });
    } catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.authWrap}>
      <Card className={s.authCard} key={cur}>
        <div className={s.steps} aria-label={`Step ${step + 1} of ${steps.length}`}>{steps.map((_, i) => <i key={i} className={i <= step ? s.on : ''} />)}</div>

        {cur === 'class' && (<>
          <div><span className={s.tag}>Step 1</span><h1 style={{ fontSize: '1.9rem' }}>Which class are you in?</h1><p className="muted">Lessons match your class. ZENITH looks back to earlier classes only when you need a refresher.</p></div>
          <div className={s.pick}>{(boards.data?.grades ?? [6, 7, 8, 9, 10]).map((g) => <button key={g} className={s.opt} aria-pressed={grade === g} onClick={() => setGrade(g)}>Class {g}</button>)}</div>
          <div><strong>Board</strong>{boards.loading ? <p className="muted sm">Loading boards…</p> : bs.length === 0 ? <p className="muted sm">No boards are set up yet.</p> : <div className={s.pick} style={{ marginTop: 8 }}>{bs.map((b) => <button key={b.id} className={s.opt} aria-pressed={chosenBoard === b.id} onClick={() => setBoard(b.id)}>{b.name}</button>)}</div>}</div>
        </>)}

        {cur === 'language' && (<>
          <div><span className={s.tag}>Step 2</span><h1 style={{ fontSize: '1.9rem' }}>Your language for explanations</h1><p className="muted">Lessons are written in English. Hindi and Telugu explanations in Ask are AI-translated and labelled until a teacher has reviewed them.</p></div>
          <div className={s.pick}>{LANGS.map((l) => <button key={l.v} className={s.opt} aria-pressed={lang === l.v} onClick={() => setLang(l.v)} lang={l.v}>{l.l}</button>)}</div>
        </>)}

        {cur === 'interests' && (<>
          <div><span className={s.tag}>Step 3</span><h1 style={{ fontSize: '1.9rem' }}>What do you want from ZENITH?</h1><p className="muted">Pick any. You can change these later.</p></div>
          <div><strong>Subjects</strong><div className={s.pick} style={{ marginTop: 8 }}>{(boards.data?.subjects ?? []).map((x) => <button key={x.id} className={s.opt} aria-pressed={subjects.includes(x.id)} onClick={() => toggle(subjects, x.id, setSubjects)}>{x.name}</button>)}</div></div>
          <div><strong>Goals</strong><div className={s.pick} style={{ marginTop: 8 }}>{GOALS.map((g) => <button key={g.v} className={s.opt} aria-pressed={goals.includes(g.v)} onClick={() => toggle(goals, g.v, setGoals)}>{g.l}</button>)}</div></div>
        </>)}

        {cur === 'name' && (<>
          <div><span className={s.tag}>{teacher ? 'Step 1' : 'Step 4'}</span><h1 style={{ fontSize: '1.9rem' }}>Choose a nickname and character</h1><p className="muted">Classmates see only your nickname and character, never your real name.</p></div>
          <label className={s.field}>Nickname<input className={s.input} value={nick} onChange={(e) => setNick(e.target.value)} maxLength={16} placeholder="e.g. Kiwi" autoFocus /></label>
          <div className={s.avatars} role="group" aria-label="Character">{AVATAR_IDS.map((a) => <button key={a} className={s.avBtn} aria-pressed={avatar === a} onClick={() => setAvatar(a)} aria-label={a}><Avatar id={a} size={52} /></button>)}</div>
        </>)}

        {cur === 'join' && (<>
          <div><span className={s.tag}>Step 5</span><h1 style={{ fontSize: '1.9rem' }}>Have a class code?</h1><p className="muted">Your teacher gives you a code like ZEN-4K7P. Skip this to learn on your own; you can join later in Settings.</p></div>
          <label className={s.field}>Class code (optional)<input className={s.input} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} maxLength={12} placeholder="ZEN-XXXX" /></label>
          <p className="sm muted"><Icon name="shield" size={16} /> Your teacher can see your progress in the class. Classmates only see your nickname.</p>
        </>)}

        <div className={s.between}>
          {step > 0 ? <Button variant="ghost" size="sm" icon="arrowL" onClick={() => setStep(step - 1)}>Back</Button> : <span />}
          {step < steps.length - 1 ? <Button variant="brand" iconRight="arrowR" disabled={!canNext} onClick={() => setStep(step + 1)}>Continue</Button> : <Button variant="brand" loading={busy} disabled={!canNext} onClick={() => void finish()} iconRight="peak">Start climbing</Button>}
        </div>
      </Card>
    </div>
  );
}
