import React, { useEffect, useState } from 'react';
import { Flame, CheckCircle2, Coins, Lock, Zap } from 'lucide-react';
import { api, StudentRewardsSummary, BadgeCatalogItem } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, Badge, Progress } from '../components/ui';
import styles from './AchievementsPage.module.css';

export const AchievementsPage: React.FC = () => {
  const [rewards, setRewards] = useState<StudentRewardsSummary | null>(null);
  const [badgeCatalog, setBadgeCatalog] = useState<BadgeCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadAchievements() {
      try {
        const [rew, bad] = await Promise.allSettled([
          api.getRewards(),
          api.getBadges()
        ]);

        if (!active) return;
        if (rew.status === 'fulfilled') setRewards(rew.value);
        if (bad.status === 'fulfilled') setBadgeCatalog(bad.value.badges);
      } catch (err) {
        console.warn('Achievements load error:', err);
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadAchievements();

    return () => {
      active = false;
    };
  }, []);

  // Honest stats from real API response: defaults strictly to 0, NEVER fabricated numbers
  const totalXp = rewards?.totalXp ?? rewards?.xp ?? 0;
  const level = rewards?.currentLevel ?? 1;
  const progressXp = rewards?.currentLevelProgressXp ?? (totalXp % 100);
  const coins = rewards?.zenithCoins ?? rewards?.coins ?? 0;
  const streak = rewards?.currentStreakDays ?? rewards?.streak ?? 0;
  const longestStreak = rewards?.longestStreakDays ?? streak;

  // Canonical badge catalog definitions: locked by default until earned in student_badges
  const canonicalBadges: BadgeCatalogItem[] = [
    {
      id: 'first_steps',
      name: 'First Steps',
      description: 'Completed your first structured curriculum lesson.',
      category: 'onboarding',
      iconUrl: '🚀',
      xpBonus: 20,
      isUnlocked: false,
      awardedAt: null
    },
    {
      id: 'curious_mind',
      name: 'Curious Mind',
      description: 'Asked your first grounded question to the Socratic AI tutor.',
      category: 'tutor',
      iconUrl: '💡',
      xpBonus: 25,
      isUnlocked: false,
      awardedAt: null
    },
    {
      id: 'practice_champion',
      name: 'Practice Champion',
      description: 'Completed 5 adaptive practice problem sets.',
      category: 'practice',
      iconUrl: '🎯',
      xpBonus: 50,
      isUnlocked: false,
      awardedAt: null
    },
    {
      id: 'consistency_star',
      name: 'Consistency Star',
      description: 'Maintained a 3-day consecutive study streak.',
      category: 'streak',
      iconUrl: '⭐',
      xpBonus: 30,
      isUnlocked: false,
      awardedAt: null
    },
    {
      id: 'concept_master',
      name: 'Concept Master',
      description: 'Achieved mastery probability P(know) >= 0.85 on any topic.',
      category: 'mastery',
      iconUrl: '👑',
      xpBonus: 60,
      isUnlocked: false,
      awardedAt: null
    },
    {
      id: 'chapter_conqueror',
      name: 'Chapter Conqueror',
      description: 'Completed all resource packages and diagnostic in a chapter.',
      category: 'completion',
      iconUrl: '🏆',
      xpBonus: 100,
      isUnlocked: false,
      awardedAt: null
    }
  ];

  // Cross-reference earned badges from profile /rewards/me if /rewards/badges catalog is absent
  const earnedBadgeMap = new Map<string, string | null>();
  if (rewards?.badges) {
    for (const b of rewards.badges) {
      earnedBadgeMap.set(b.id, b.awardedAt || null);
    }
  }

  // Use backend catalogue when available, fallback to canonical definitions (all locked by default)
  const baseList = badgeCatalog.length > 0 ? badgeCatalog : canonicalBadges;
  const badges: BadgeCatalogItem[] = baseList.map((b) => {
    const isEarnedInProfile = earnedBadgeMap.has(b.id);
    const isUnlocked = b.isUnlocked || isEarnedInProfile;
    const awardedAt = b.awardedAt || earnedBadgeMap.get(b.id) || null;
    return {
      ...b,
      isUnlocked,
      awardedAt
    };
  });

  // Calculate dynamic days in current month and current date
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const currentDay = now.getDate();

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        Loading Achievements & Badges…
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* 1. Level & Coins Header */}
      <section className={styles.levelCard}>
        <div className={styles.levelInfo}>
          <div className={styles.levelBadge}>
            <small>LVL</small>
            <span>{level}</span>
          </div>
          <div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-xl)', fontWeight: 800 }}>
              Scholar Rank {level}
            </h2>
            <div className={styles.levelProgressWrapper}>
              <Progress
                value={(progressXp / 100) * 100}
                label={`${progressXp} / 100 XP to Level ${level + 1}`}
                color="saffron"
              />
            </div>
          </div>
        </div>

        <div className={styles.coinsPill}>
          <Coins size={18} color="#D97706" />
          <span>{coins} Zenith Coins</span>
        </div>
      </section>

      {/* 2. Streak Calendar & Learning History Grid */}
      <section className={styles.grid}>
        {/* 30-Day Streak Calendar */}
        <Card elevation={2}>
          <CardHeader>
            <CardTitle>Streak Calendar</CardTitle>
            <Badge variant="terracotta">
              <Flame size={12} style={{ marginRight: 4 }} /> {streak} Day Streak
            </Badge>
          </CardHeader>
          <CardContent>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
              Calculated daily at midnight in <strong style={{ color: 'var(--ink-charcoal)' }}>Asia/Kolkata</strong>. Longest streak: {longestStreak} days.
            </p>

            <div className={styles.calendarGrid}>
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
                <div key={d} className={styles.dayHeader}>{d}</div>
              ))}
              {Array.from({ length: daysInMonth }).map((_, idx) => {
                const dayNum = idx + 1;
                // Active on recent days of streak (streak > 0)
                const isActive = streak > 0 && dayNum <= currentDay && dayNum > (currentDay - streak);
                const isToday = dayNum === currentDay;

                return (
                  <div
                    key={idx}
                    className={`${styles.calendarDay} ${isActive ? styles.dayActive : ''}`}
                    title={isToday ? 'Today' : `Day ${dayNum}`}
                  >
                    <span>{dayNum}</span>
                    {isActive && <Flame size={10} color="#EA580C" />}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Learning History & Recent Events */}
        <Card elevation={2}>
          <CardHeader>
            <CardTitle>Reward Events</CardTitle>
            <Zap size={16} color="#D97706" />
          </CardHeader>
          <CardContent>
            {rewards?.recentEvents && rewards.recentEvents.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {rewards.recentEvents.slice(0, 5).map((evt, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 'var(--space-3)',
                      border: 'var(--border-hairline)',
                      borderRadius: 'var(--radius-micro)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: 'var(--text-xs)' }}>{evt.eventType.replace(/_/g, ' ').toUpperCase()}</strong>
                      <div style={{ fontSize: '10.5px', color: 'var(--ink-secondary)' }}>
                        {new Date(evt.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    <Badge variant="saffron" size="sm">+{evt.xpAwarded} XP</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ink-secondary)' }}>
                Solve practice questions or complete curriculum lessons to record reward events.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      {/* 3. Badges Showcase Grid */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-xl)', fontWeight: 800 }}>
            Badges Showcase
          </h2>
          <Badge variant="olive">
            {badges.filter((b) => b.isUnlocked).length} / {badges.length} Unlocked
          </Badge>
        </div>

        <div className={styles.badgesGrid}>
          {badges.map((b) => (
            <div
              key={b.id}
              className={`${styles.badgeCard} ${b.isUnlocked ? styles.badgeUnlocked : styles.badgeLocked}`}
            >
              <div className={styles.badgeIcon}>
                <span style={{ fontSize: '24px' }}>{b.iconUrl || '🏅'}</span>
              </div>
              <strong style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-sm)' }}>
                {b.name}
              </strong>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
                {b.description}
              </p>
              <div style={{ marginTop: 'auto' }}>
                {b.isUnlocked ? (
                  <Badge variant="olive" size="sm">
                    <CheckCircle2 size={10} style={{ marginRight: 3 }} /> Unlocked
                  </Badge>
                ) : (
                  <Badge variant="neutral" size="sm">
                    <Lock size={10} style={{ marginRight: 3 }} /> Locked (+{b.xpBonus} XP)
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AchievementsPage;
