import { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Avatar, AVATAR_IDS, Icon } from '../icons/Icon';
import { Button, Card, Segmented, useToast } from '../ui/kit';
import type { Profile } from '../api/types';
import s from './pages.module.css';

import { InstallApp } from '../ui/InstallApp';

export default function Settings() {
  const { profile, setProfile, theme, setTheme, logout } = useAuth();
  const toast = useToast();
  const [nick, setNick] = useState(profile?.nickname ?? '');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  if (!profile) return null;

  async function save(patch: Record<string, unknown>, msg = 'Saved') {
    setBusy(true);
    try { setProfile(await api<Profile>('/profile', { method: 'PUT', body: patch })); toast(msg, 'ok'); }
    catch (e) { toast((e as Error).message, 'err'); } finally { setBusy(false); }
  }

  return (
    <div className={s.stack} style={{ maxWidth: 760 }}>
      <h1 className={s.title}>Settings</h1>
      <InstallApp />

      <Card>
        <h3>Your character</h3>
        <div className={s.avatars} style={{ margin: '14px 0' }}>{AVATAR_IDS.map((a) => <button key={a} className={s.avBtn} aria-pressed={profile.avatar === a} aria-label={a} onClick={() => void save({ avatar: a })}><Avatar id={a} size={52} /></button>)}</div>
        <label className={s.field}>Nickname (classmates see this)
          <div className={s.row}><input className={s.input} style={{ flex: 1 }} value={nick} onChange={(e) => setNick(e.target.value)} maxLength={16} /><Button size="sm" variant="brand" loading={busy} disabled={nick.trim().length < 2 || nick === profile.nickname} onClick={() => void save({ nickname: nick.trim() })}>Save</Button></div>
        </label>
      </Card>

      {profile.role === 'student' && (
        <Card>
          <h3>Learning</h3>
          <div className={s.stack} style={{ marginTop: 14 }}>
            <div><span className="sm muted">Class</span><div><Segmented label="Class" value={profile.grade ?? 7} onChange={(g) => void save({ grade: g })} options={[6, 7, 8, 9, 10].map((g) => ({ value: g, label: String(g) }))} /></div></div>
            <div><span className="sm muted">Explanation language</span><div><Segmented label="Language" value={profile.language} onChange={(l) => void save({ language: l })} options={[{ value: 'en', label: 'English' }, { value: 'hi', label: 'हिन्दी' }, { value: 'te', label: 'తెలుగు' }]} /></div></div>
            <label className={s.field}>Join a class
              <div className={s.row}><input className={s.input} style={{ flex: 1 }} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="ZEN-XXXX" maxLength={12} /><Button size="sm" variant="ghost" disabled={code.length < 4} loading={busy} onClick={() => void save({ classCode: code }, 'Joined your class').then(() => setCode(''))}>Join</Button></div>
            </label>
          </div>
        </Card>
      )}

      {profile.role === 'student' && (
        <Card>
          <h3>League</h3>
          <label style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, fontWeight: 700 }}>
            <input type="checkbox" checked={!profile.leagueOptOut} onChange={(e) => void save({ leagueOptOut: !e.target.checked })} style={{ width: 22, height: 22, accentColor: 'var(--brand)' }} />
            Show me in my class league (classmates see only my nickname and character)
          </label>
        </Card>
      )}

      <Card>
        <h3>Look and feel</h3>
        <div style={{ marginTop: 14 }}><Segmented label="Theme" value={theme} onChange={setTheme} options={[{ value: 'system', label: 'Match device' }, { value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }]} /></div>
      </Card>

      <Card>
        <h3>Privacy</h3>
        <p className="muted sm" style={{ margin: '8px 0 14px' }}>ZENITH saves your answers to help you learn and to show your teacher. We never share your name or email with AI helpers.</p>
        <div className={s.row}>
          <Button variant="ghost" size="sm" icon="download" onClick={() => toast('Data export is prepared by your teacher or ZENITH admin on request.', 'info')}>Export my data</Button>
          <Button variant="danger" size="sm" icon="logout" onClick={logout}>Sign out</Button>
        </div>
        <p className="sm muted" style={{ marginTop: 12 }}><Icon name="shield" size={16} /> Ask your teacher or guardian if you want your account deleted.</p>
      </Card>
    </div>
  );
}
