import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  AlertTriangle,
  BookOpen,
  Compass,
  Download,
  GraduationCap,
  Home,
  LayoutDashboard,
  MessageCircleQuestion,
  Network,
  Sparkles,
  Target,
  Trophy
} from 'lucide-react';
import { syncManager } from '../services/syncManager';
import { useAuth } from '../context/AuthContext';
import { AuthModal } from './AuthModal';
import { api } from '../services/api';
import { openAskZenith } from './AskZenith';
import styles from './Navigation.module.css';

const initialsFor = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'Z';

export const Navigation: React.FC = () => {
  const { user, logout, openTour } = useAuth();
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [lastSyncError, setLastSyncError] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [lessonHref, setLessonHref] = useState('/');

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    const unsubscribe = syncManager.subscribe((syncing, count, lastError) => {
      setIsSyncing(syncing);
      setPendingCount(count);
      setLastSyncError(lastError);
    });
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    void syncManager.refreshPending();
  }, [user]);

  useEffect(() => {
    if (!user || user.role === 'teacher') {
      setLessonHref('/');
      return;
    }
    let cancelled = false;
    api.getLearningPaths()
      .then((paths) => {
        if (cancelled) return;
        const path = paths[0];
        const ready = path?.lessons?.find((lesson) => lesson.status === 'ready');
        const target = ready?.id || path?.firstLessonId;
        setLessonHref(target ? `/learn/${target}?pathId=${path.id}` : '/');
      })
      .catch(() => {
        if (!cancelled) setLessonHref('/');
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink;

  return (
    <>
      <aside className={styles.sidebar}>
        <NavLink to={user?.role === 'teacher' ? '/teacher' : '/'} className={styles.brand} title="ZENITH home">
          <span className={styles.brandMark} aria-hidden="true">
            <img src="/zenith-mark.svg" alt="ZENITH" width={34} height={34} />
          </span>
          <span className={styles.brandText}>
            <span className={styles.brandName}>ZENITH</span>
            <span className={styles.brandTag}>Adaptive Companion</span>
          </span>
        </NavLink>

        <nav className={styles.navLinks} aria-label="Primary Navigation">
          <span className={styles.navLabel} aria-hidden="true">Study Desk</span>
          
          <NavLink to="/" end className={linkClass}>
            <Home size={16} aria-hidden="true" /> Home
          </NavLink>

          <NavLink to="/explore" className={linkClass}>
            <Compass size={16} aria-hidden="true" /> Explore
          </NavLink>

          <NavLink to="/practice" className={linkClass}>
            <Target size={16} aria-hidden="true" /> Practice
          </NavLink>

          <NavLink to="/map" className={linkClass}>
            <Network size={16} aria-hidden="true" /> Concept Map
          </NavLink>

          <NavLink to="/achievements" className={linkClass}>
            <Trophy size={16} aria-hidden="true" /> Badges & XP
          </NavLink>

          <NavLink to="/ask" className={linkClass}>
            <Sparkles size={16} aria-hidden="true" /> Socratic Tutor
          </NavLink>

          {lessonHref !== '/' && (
            <NavLink to={lessonHref} className={linkClass}>
              <BookOpen size={16} aria-hidden="true" /> Active Lesson
            </NavLink>
          )}

          {user && (
            <>
              <NavLink to="/dashboard" className={linkClass}>
                <LayoutDashboard size={16} aria-hidden="true" /> Dashboard
              </NavLink>

              <NavLink to="/library" className={linkClass}>
                <Download size={16} aria-hidden="true" /> Downloads
              </NavLink>

              <NavLink to="/doubts" className={linkClass}>
                <MessageCircleQuestion size={16} aria-hidden="true" /> Doubts
                {pendingCount > 0 ? <span className={styles.countBadge}>{pendingCount}</span> : null}
              </NavLink>
            </>
          )}

          {user?.canTeach && (
            <NavLink to="/teacher" className={linkClass}>
              <GraduationCap size={16} aria-hidden="true" /> Classroom
            </NavLink>
          )}

          <button
            type="button"
            className={styles.navButton}
            onClick={openAskZenith}
            title="Ask the ZENITH AI tutor a question"
          >
            <Sparkles size={16} aria-hidden="true" /> Quick Ask
          </button>
        </nav>

        <div className={styles.sidebarFoot}>
          <div
            className={`${styles.badge} ${isOnline ? styles.badgeOnline : styles.badgeOffline}`}
            title={
              isOnline
                ? 'Connected'
                : 'Offline. Work is saved on this device and syncs when you reconnect.'
            }
          >
            <span className={styles.dot} />
            {isOnline ? 'Online' : 'Offline'}
          </div>
          {pendingCount > 0 && isOnline && (
            <button
              type="button"
              className={`${styles.syncButton} ${lastSyncError ? styles.syncButtonError : ''}`}
              onClick={() => void syncManager.syncPendingData()}
              disabled={isSyncing}
            >
              {lastSyncError ? <AlertTriangle size={14} aria-hidden="true" /> : null}
              {isSyncing ? 'Syncing…' : lastSyncError ? 'Last sync failed — Retry' : 'Sync now'}
            </button>
          )}
          <button type="button" className={styles.tourTriggerButton} onClick={openTour}>
            <Sparkles size={14} aria-hidden="true" />
            {user ? 'How ZENITH works' : 'Get started'}
          </button>
          {user ? (
            <div className={styles.userBlock}>
              <span className={styles.avatar} aria-hidden="true">{initialsFor(user.displayName)}</span>
              <span className={styles.userCopy}>
                <span className={styles.userName}>{user.displayName}</span>
                <span className={styles.userRoleBadge}>{user.role === 'teacher' ? 'Teacher' : 'Student'}</span>
              </span>
              <button type="button" className={styles.logoutBtn} onClick={() => void logout()}>
                Sign out
              </button>
            </div>
          ) : (
            <button type="button" className={styles.loginBtn} onClick={() => setIsAuthModalOpen(true)}>
              Sign in
            </button>
          )}
        </div>
      </aside>
      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </>
  );
};
