import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Flame, Zap, Trophy, BookOpen, Sparkles, ArrowRight } from 'lucide-react';
import {
  api,
  StudentRewardsSummary,
  LibraryCatalogueResponse,
  PracticeRecommendationResponse,
  TutorThreadItem
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button, Card, CardHeader, CardTitle, CardContent, Badge, Progress } from '../components/ui';
import styles from './HomePage.module.css';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [rewards, setRewards] = useState<StudentRewardsSummary | null>(null);
  const [catalogue, setCatalogue] = useState<LibraryCatalogueResponse | null>(null);
  const [recommendation, setRecommendation] = useState<PracticeRecommendationResponse | null>(null);
  const [, setThreads] = useState<TutorThreadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [claimStatus, setClaimStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const [rewRes, catRes, recRes, thrRes] = await Promise.allSettled([
          api.getRewards(),
          api.getLibraryCatalogue(10, 'subject-math'),
          api.getPracticeRecommendation('real-numbers'),
          api.listTutorThreads()
        ]);

        if (!active) return;

        if (rewRes.status === 'fulfilled') setRewards(rewRes.value);
        if (catRes.status === 'fulfilled') setCatalogue(catRes.value);
        if (recRes.status === 'fulfilled') setRecommendation(recRes.value);
        if (thrRes.status === 'fulfilled') setThreads(thrRes.value);
      } catch (err) {
        console.warn('Dashboard load error:', err);
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [user]);

  const handleClaimDaily = async () => {
    try {
      await api.claimDailyLogin();
      setClaimStatus('Daily +10 XP & Coin Claimed!');
      const updated = await api.getRewards();
      setRewards(updated);
    } catch {
      setClaimStatus('Already claimed for today.');
    }
  };

  const displayName = user?.displayName || 'Learner';
  // Rule 2 Compliance: True stats strictly from database; streak defaults to 0 (not 1)
  const totalXp = rewards?.totalXp ?? rewards?.xp ?? 0;
  const level = rewards?.currentLevel ?? 1;
  const progressXp = rewards?.currentLevelProgressXp ?? (totalXp % 100);
  const streak = rewards?.currentStreakDays ?? rewards?.streak ?? 0;
  const unlockedBadgesCount = rewards?.badges?.length ?? 0;

  // Real first chapter from catalogue or null: NO hardcoded fake 20% completion object
  const firstChapter = catalogue?.chapters && catalogue.chapters.length > 0 ? catalogue.chapters[0] : null;

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        Loading Your Study Desk…
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* 1. Welcome Desk Banner */}
      <section className={styles.welcomeBanner}>
        <div className={styles.welcomeCopy}>
          <span className={styles.kicker}>The Learning Desk</span>
          <h1 className={styles.title}>Welcome back, {displayName}!</h1>
          <div className={styles.streakBanner}>
            <Flame size={18} color="#EA580C" />
            <span>🔥 {streak} Day Streak — Active in Asia/Kolkata</span>
          </div>
        </div>

        <div>
          <Button
            variant="primary"
            size="md"
            onClick={handleClaimDaily}
            leftIcon={<Sparkles size={16} />}
          >
            {claimStatus || 'Claim Daily Bonus (+10 XP)'}
          </Button>
        </div>
      </section>

      {/* 2. 4 Gamification Metric Cards */}
      <section className={styles.statsGrid}>
        <Card elevation={2} className={styles.statCard}>
          <CardContent>
            <div className={styles.statCardHead}>
              <span className={styles.statLabel}>Total XP</span>
              <Zap size={18} color="#D97706" />
            </div>
            <div className={styles.statValue}>{totalXp} XP</div>
            <div style={{ marginTop: '8px' }}>
              <Progress
                value={(progressXp / 100) * 100}
                label={`Lvl ${level} Progress`}
                showValue
                color="saffron"
              />
            </div>
          </CardContent>
        </Card>

        <Card elevation={2} className={styles.statCard}>
          <CardContent>
            <div className={styles.statCardHead}>
              <span className={styles.statLabel}>Mastery Level</span>
              <Trophy size={18} color="#1B4965" />
            </div>
            <div className={styles.statValue}>Level {level}</div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginTop: '8px' }}>
              {100 - progressXp} XP to Level {level + 1}
            </p>
          </CardContent>
        </Card>

        <Card elevation={2} className={styles.statCard}>
          <CardContent>
            <div className={styles.statCardHead}>
              <span className={styles.statLabel}>Day Streak</span>
              <Flame size={18} color="#C84B31" />
            </div>
            <div className={styles.statValue}>{streak} Days</div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginTop: '8px' }}>
              Study today to protect your streak
            </p>
          </CardContent>
        </Card>

        <Card elevation={2} className={styles.statCard}>
          <CardContent>
            <div className={styles.statCardHead}>
              <span className={styles.statLabel}>Achievements</span>
              <Badge variant="olive" size="sm">Active</Badge>
            </div>
            <div className={styles.statValue}>{unlockedBadgesCount} Badges</div>
            <div style={{ marginTop: '8px' }}>
              <Button
                variant="outline"
                size="sm"
                fullWidth
                onClick={() => navigate('/achievements')}
              >
                View Showcase
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 3. Main Action Grid */}
      <section className={styles.mainGrid}>
        {/* Left Column: Continue Learning & Chapters */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <Card elevation={2}>
            {firstChapter ? (
              <>
                <CardHeader>
                  <CardTitle>Continue Studying</CardTitle>
                  <Badge variant="saffron">Class 10 CBSE Math</Badge>
                </CardHeader>
                <CardContent>
                  <h4 style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-2)' }}>
                    Chapter {firstChapter.chapterNumber}: {firstChapter.title}
                  </h4>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ink-secondary)', marginBottom: 'var(--space-4)' }}>
                    {firstChapter.description}
                  </p>
                  <Progress
                    value={firstChapter.completionPct ?? 0}
                    label="Chapter Progress"
                    showValue
                    color="olive"
                  />
                  <div className={styles.cardActionRow}>
                    <Button
                      variant="primary"
                      onClick={() => navigate(`/chapter/${firstChapter.slug}`)}
                      rightIcon={<ArrowRight size={16} />}
                    >
                      Continue Studying
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate('/explore')}
                      leftIcon={<BookOpen size={16} />}
                    >
                      All Chapters
                    </Button>
                  </div>
                </CardContent>
              </>
            ) : (
              <>
                <CardHeader>
                  <CardTitle>Start Learning</CardTitle>
                  <Badge variant="saffron">Class 10 CBSE Math</Badge>
                </CardHeader>
                <CardContent>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ink-secondary)', marginBottom: 'var(--space-4)' }}>
                    No chapter in progress yet. Explore the CBSE Class 10 curriculum library to begin your learning journey.
                  </p>
                  <Button
                    variant="primary"
                    onClick={() => navigate('/explore')}
                    rightIcon={<ArrowRight size={16} />}
                  >
                    Browse Curriculum Library
                  </Button>
                </CardContent>
              </>
            )}
          </Card>

          {/* Quick Chapters Rail */}
          <div className={styles.quickChapters}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-md)', fontWeight: 800 }}>
                Curriculum Chapters
              </h3>
              <Button variant="ghost" size="sm" onClick={() => navigate('/explore')}>
                Explore All
              </Button>
            </div>

            <div className={styles.chapterCardStack}>
              {catalogue?.chapters && catalogue.chapters.length > 0 ? (
                catalogue.chapters.map((ch) => (
                  <div
                    key={ch.slug}
                    className={styles.chapterRowItem}
                    onClick={() => navigate(`/chapter/${ch.slug}`)}
                  >
                    <div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
                        Chapter {ch.chapterNumber}
                      </div>
                      <strong style={{ fontSize: 'var(--text-sm)' }}>{ch.title}</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                      <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}>
                        {ch.completionPct || 0}%
                      </span>
                      <ArrowRight size={14} color="var(--ink-secondary)" />
                    </div>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
                  Loading chapter syllabus…
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Weakest Prerequisite Gap & AI Tutor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {/* Smart Practice Recommendation */}
          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Recommended Focus</CardTitle>
              <Badge variant="terracotta">Adaptive Gap</Badge>
            </CardHeader>
            <CardContent>
              {recommendation ? (
                <>
                  <h4 style={{ fontSize: 'var(--text-md)', marginBottom: 'var(--space-1)' }}>
                    {recommendation.conceptTitle}
                  </h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginBottom: 'var(--space-4)' }}>
                    {recommendation.reason}
                  </p>
                  <Button
                    variant="accent"
                    size="sm"
                    fullWidth
                    onClick={() => navigate(recommendation ? `/practice?chapter=${encodeURIComponent(recommendation.chapterSlug)}&concept=${encodeURIComponent(recommendation.conceptId)}` : '/practice')}
                    rightIcon={<ArrowRight size={14} />}
                  >
                    Practice This Concept
                  </Button>
                </>
              ) : (
                <>
                  <h4 style={{ fontSize: 'var(--text-md)', marginBottom: 'var(--space-1)' }}>
                    Diagnostic Assessment
                  </h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginBottom: 'var(--space-4)' }}>
                    Sit a 6-question calibration diagnostic to detect your conceptual prerequisite strengths.
                  </p>
                  <Button
                    variant="accent"
                    size="sm"
                    fullWidth
                    onClick={() => navigate('/practice?chapter=real-numbers&mode=diagnostic')}
                    rightIcon={<ArrowRight size={14} />}
                  >
                    Begin Diagnostic
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Socratic Doubt Asking Card */}
          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Ask Socratic Tutor</CardTitle>
              <Badge variant="ultramarine">Grounded AI</Badge>
            </CardHeader>
            <CardContent>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginBottom: 'var(--space-4)' }}>
                Stuck on a theorem proof or formula derivation? Ask our Socratic Tutor for step-by-step guidance.
              </p>
              <Button
                variant="outline"
                size="sm"
                fullWidth
                onClick={() => navigate('/tutor')}
                leftIcon={<Sparkles size={14} />}
              >
                Open Tutor Thread
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
