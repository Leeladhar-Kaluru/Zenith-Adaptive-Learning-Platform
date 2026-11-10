import React, { useState, useEffect } from 'react';
import { Flame, Zap, Wifi, WifiOff } from 'lucide-react';
import { Logo } from './Logo';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import styles from './Header.module.css';

export interface HeaderProps {
  title?: string;
  streakDays?: number;
  xp?: number;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  streakDays: propStreak,
  xp: propXp
}) => {
  const { user } = useAuth();
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [fetchedStats, setFetchedStats] = useState<{ streak: number; xp: number } | null>(null);
  const [loadingStats, setLoadingStats] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Wire real student stats if props are not provided
  useEffect(() => {
    if (!user) {
      setFetchedStats(null);
      setLoadingStats(false);
      return;
    }

    // If both props are provided externally, skip API fetch
    if (propStreak !== undefined && propXp !== undefined) {
      setFetchedStats({ streak: propStreak, xp: propXp });
      setLoadingStats(false);
      return;
    }

    let active = true;
    setLoadingStats(true);

    api.getRewards()
      .then((data) => {
        if (!active) return;
        setFetchedStats({
          streak: data.currentStreakDays ?? data.streak ?? 0,
          xp: data.totalXp ?? data.xp ?? 0
        });
      })
      .catch((err) => {
        if (!active) return;
        console.warn('Header: Failed to fetch student rewards profile:', err);
        // Honest fallback to 0 when API fails, NEVER fabricated fake stats
        setFetchedStats({ streak: 0, xp: 0 });
      })
      .finally(() => {
        if (active) setLoadingStats(false);
      });

    return () => {
      active = false;
    };
  }, [user, propStreak, propXp]);

  const displayStreak = propStreak !== undefined ? propStreak : fetchedStats?.streak;
  const displayXp = propXp !== undefined ? propXp : fetchedStats?.xp;

  return (
    <header className={styles.header}>
      <div className={styles.leftSection}>
        <div className={styles.mobileLogo}>
          <Logo size="sm" showSubtitle={false} />
        </div>
        {title && <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}>{title}</span>}
      </div>

      <div className={styles.rightSection}>
        {user && (
          <>
            <div className={`${styles.statPill} ${styles.streakPill}`} title="Consecutive Day Streak (Asia/Kolkata)">
              <Flame size={14} color="#EA580C" />
              <span>{loadingStats && displayStreak === undefined ? '--' : `${displayStreak ?? 0}D`}</span>
            </div>

            <div className={`${styles.statPill} ${styles.xpPill}`} title="Total Earned XP">
              <Zap size={14} color="#D97706" />
              <span>{loadingStats && displayXp === undefined ? '--' : `${displayXp ?? 0} XP`}</span>
            </div>
          </>
        )}

        <div className={`${styles.statusIndicator} ${isOnline ? styles.online : styles.offline}`}>
          {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{isOnline ? 'Online' : 'Offline'}</span>
        </div>
      </div>
    </header>
  );
};
