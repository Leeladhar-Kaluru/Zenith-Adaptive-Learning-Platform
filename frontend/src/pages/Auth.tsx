import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Card, Segmented } from '../ui/kit';
import { PublicBar } from './Landing';
import { ApiError } from '../api/client';
import { passwordProblems } from '../lib/password';
import s from './pages.module.css';

export default function Auth({ mode }: { mode: 'signin' | 'signup' }) {
  const { login, signup } = useAuth();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const [role, setRole] = useState<'student' | 'teacher'>('student');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [show, setShow] = useState(false);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const up = mode === 'signup';

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr('');
    if (up && !agree) { setErr('Please confirm the consent statement to continue.'); return; }
    if (up && passwordProblems(pw).length) { setErr('Please choose a stronger password: ' + passwordProblems(pw).join(', ').toLowerCase() + '.'); return; }
    if (up && pw !== pw2) { setErr('The two passwords do not match.'); return; }
    setBusy(true);
    try {
      const p = up ? await signup({ email, password: pw, displayName: name.trim(), role, consent: agree }) : await login(email, pw);
      if (!p) { setErr('Check your email to confirm your account, then sign in.'); return; }
      nav(p.onboardingCompleted ? from ?? '/' : '/onboarding', { replace: true });
    } catch (x) {
      setErr(x instanceof ApiError ? x.message : 'Something went wrong. Please try again.');
    } finally { setBusy(false); }
  }

  return (
    <div className={s.pub}>
      <PublicBar />
      <div className={s.authWrap}>
        <Card className={s.authCard}>
          <div>
            <span className={s.tag}>{up ? 'Welcome' : 'Welcome back'}</span>
            <h1 style={{ fontSize: '2rem' }}>{up ? 'Start climbing' : 'Sign in to ZENITH'}</h1>
          </div>
          <form onSubmit={submit} className={s.stack} noValidate>
            {up && <Segmented label="I am a" value={role} onChange={setRole} options={[{ value: 'student', label: 'Student' }, { value: 'teacher', label: 'Teacher' }]} />}
            {up && (
              <label className={s.field}>Your name
                <input className={s.input} value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" placeholder="Only your teacher sees this" />
              </label>
            )}
            <label className={s.field}>Email
              <input className={s.input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" inputMode="email" />
            </label>
            <label className={s.field}>Password
              <span className={s.pwRow}>
                <input className={s.input} type={show ? 'text' : 'password'} value={pw} onChange={(e) => setPw(e.target.value)} required autoComplete={up ? 'new-password' : 'current-password'} />
                <button type="button" className={s.pwToggle} aria-pressed={show} onClick={() => setShow((v) => !v)}>{show ? 'Hide' : 'Show'}<span className="sr-only"> password</span></button>
              </span>
            </label>
            {up && (
              <>
                <label className={s.field}>Confirm password
                  <input className={s.input} type={show ? 'text' : 'password'} value={pw2} onChange={(e) => setPw2(e.target.value)} required autoComplete="new-password" aria-invalid={pw2.length > 0 && pw !== pw2} />
                </label>
                <ul className={`sm ${s.rules}`} aria-live="polite">
                  {['At least 8 characters', 'At least one letter', 'At least one number'].map((r) => (
                    <li key={r} className={passwordProblems(pw).includes(r) ? '' : s.ok}>{r}</li>
                  ))}
                  <li className={pw2 && pw === pw2 ? s.ok : ''}>Both passwords match</li>
                </ul>
              </>
            )}
            {up && (
              <label className="sm muted" style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} style={{ width: 22, height: 22, marginTop: 2, accentColor: 'var(--brand)' }} />
                <span>
                  {role === 'student'
                    ? 'I am 18 or older, or my parent, guardian or school has agreed that I can use ZENITH. ZENITH saves my answers to help me learn and to show my teacher.'
                    : 'I am a teacher and will use ZENITH only with students whose guardians or school have agreed.'}
                </span>
              </label>
            )}
            {err && <div className={s.err} role="alert">{err}</div>}
            <Button type="submit" variant="brand" block loading={busy}>{up ? 'Create account' : 'Sign in'}</Button>
          </form>
          <p className="sm muted" style={{ textAlign: 'center' }}>
            {up ? <>Already have an account? <Link to="/signin" style={{ fontWeight: 800, textDecoration: 'underline' }}>Sign in</Link></> : <>New here? <Link to="/signup" style={{ fontWeight: 800, textDecoration: 'underline' }}>Create an account</Link></>}
          </p>
        </Card>
      </div>
    </div>
  );
}
