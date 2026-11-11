import { Suspense, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Avatar, Icon } from '../icons/Icon';
import { Chip } from '../ui/kit';
import { RouteLoader } from '../fx/fx';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../api/useApi';
import type { Today } from '../api/types';
import s from './shell.module.css';

const STUDENT = [
  { to: '/home', icon: 'home', label: 'Home' },
  { to: '/learn', icon: 'book', label: 'Learn' },
  { to: '/practice', icon: 'target', label: 'Practice' },
  { to: '/explore', icon: 'puzzle', label: 'Explore' },
  { to: '/classes', icon: 'people', label: 'Classes' },
  { to: '/ask', icon: 'chat', label: 'Ask' },
  { to: '/progress', icon: 'peak', label: 'Progress' },
];
const TEACHER = [
  { to: '/teacher', icon: 'people', label: 'Classes' },
  { to: '/learn', icon: 'book', label: 'Library' },
  { to: '/settings', icon: 'gear', label: 'Settings' },
];
const REVIEWER = [
  { to: '/review', icon: 'clipboard', label: 'Review' },
  { to: '/learn', icon: 'book', label: 'Library' },
  { to: '/settings', icon: 'gear', label: 'Settings' },
];

function Stats() {
  const { data, reload } = useApi<Today>('/stats');
  useEffect(() => {
    window.addEventListener('zenith:progress', reload);
    return () => window.removeEventListener('zenith:progress', reload);
  }, [reload]);
  if (!data) return null;
  return (
    <>
      <Chip tone="hi" icon="flame">{data.streak.days}</Chip>
      <span className={s.hideSm}><Chip icon="bolt">{data.xp.xp} XP</Chip></span>
    </>
  );
}

export default function Shell() {
  const { profile, logout, theme, setTheme } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [min, setMin] = useState(() => localStorage.getItem('zenith_rail') === '1');
  const [menu, setMenu] = useState(false);
  useEffect(() => setMenu(false), [loc.pathname]);
  useEffect(() => { localStorage.setItem('zenith_rail', min ? '1' : '0'); }, [min]);
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);

  const items = profile?.role === 'teacher' ? TEACHER : profile?.role === 'reviewer' || profile?.role === 'admin' ? REVIEWER : STUDENT;
  const dark = theme === 'dark' || (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <>
      <a className={s.skip} href="#main">Skip to content</a>
      <div className={`${s.app} ${min ? s.min : ''}`}>
        <aside className={s.rail} aria-label="Primary">
          <div className={s.brand}>
            <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden="true"><path d="M2 27L13 7l5 9 3-5 9 16z" fill="var(--brand)" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" /><circle cx="24" cy="8" r="3.4" fill="var(--hi)" stroke="var(--ink)" strokeWidth="2" /></svg>
            <span className={s.label}>ZENITH</span>
          </div>
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} className={s.item} viewTransition>
              <Icon name={i.icon} size={22} /><span className={s.label}>{i.label}</span>
            </NavLink>
          ))}
          <div className={s.grow} />
          <p className={`hand ${s.note}`} style={{ padding: '0 12px' }}>your next step is waiting</p>
          <button className={s.item} onClick={() => setMin((m) => !m)} aria-label={min ? 'Expand sidebar' : 'Collapse sidebar'}>
            <Icon name={min ? 'chevR' : 'arrowL'} size={22} /><span className={s.label}>Collapse</span>
          </button>
        </aside>

        <div className={s.main}>
          <header className={s.top}>
            {profile?.grade && <Chip>Class {profile.grade}</Chip>}
            <span className={s.spacer} />
            {profile?.role === 'student' && <Stats />}
            <button className={s.iconBtn} onClick={() => setTheme(dark ? 'light' : 'dark')} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}>
              <Icon name={dark ? 'sun' : 'moon'} size={22} />
            </button>
            {profile && (
              <button className={s.me} onClick={() => setMenu((m) => !m)} aria-expanded={menu} aria-haspopup="menu">
                <Avatar id={profile.avatar} size={34} />
                <span className={s.hideSm}>{profile.nickname}</span>
              </button>
            )}
          </header>
          {menu && (
            <div className={s.menu} role="menu">
              <NavLink to="/settings" className={s.item} role="menuitem"><Icon name="gear" size={20} />Settings</NavLink>
              <NavLink to="/offline" className={s.item} role="menuitem"><Icon name="download" size={20} />Offline lessons</NavLink>
              <button className={s.item} role="menuitem" onClick={() => { logout(); nav('/'); }}><Icon name="logout" size={20} />Sign out</button>
            </div>
          )}
          <main id="main" className={s.page} key={loc.pathname.split('/')[1]}>
            <Suspense fallback={<RouteLoader />}><Outlet /></Suspense>
          </main>
        </div>
      </div>

      <nav className={s.bottom} aria-label="Primary">
        {items.map((i) => (
          <NavLink key={i.to} to={i.to} viewTransition><Icon name={i.icon} size={24} />{i.label}</NavLink>
        ))}
      </nav>
    </>
  );
}
