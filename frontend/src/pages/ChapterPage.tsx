import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Network, Target, Clock, CheckCircle2, ChevronRight, Layers } from 'lucide-react';
import { api, ChapterDetailResponse } from '../services/api';
import { Button, Card, CardHeader, CardTitle, CardContent, Badge, Progress } from '../components/ui';
import styles from './ChapterPage.module.css';

export const ChapterPage: React.FC = () => {
  const { slug = 'real-numbers' } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const [chapter, setChapter] = useState<ChapterDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadChapter() {
      try {
        const res = await api.getChapter(slug);
        if (active) setChapter(res);
      } catch (err: any) {
        if (active) setError(err.message || 'Chapter not found.');
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadChapter();

    return () => {
      active = false;
    };
  }, [slug]);

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        Loading Chapter Syllabus…
      </div>
    );
  }

  if (error && !chapter) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center' }}>
        <p style={{ color: 'var(--accent-terracotta)', marginBottom: 'var(--space-4)' }}>{error}</p>
        <Button variant="outline" onClick={() => navigate('/explore')}>Back to Explore</Button>
      </div>
    );
  }

  const title = chapter?.title || slug.replace(/-/g, ' ').toUpperCase();
  const description = chapter?.description || 'CBSE Grade 10 Mathematics standard curriculum syllabus chapter.';
  // Rule 2 Compliance: Use real chapter resources and honest progress; NEVER hardcode fallback completed resources
  const resources = chapter?.resources ?? [];
  const concepts = chapter?.concepts ?? [];
  const completionPct = chapter?.completionPct ?? 0;

  return (
    <div className={styles.page}>
      {/* 1. Chapter Header */}
      <section className={styles.headerCard}>
        <div className={styles.kickerRow}>
          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
            <Badge variant="saffron">Chapter {chapter?.chapterNumber || 1}</Badge>
            <Badge variant="neutral">
              Class {chapter?.grade || 10} CBSE {chapter?.subjectId?.includes('science') ? 'Science' : 'Mathematics'}
            </Badge>
          </div>
          {chapter?.isEnrolled && <Badge variant="olive">Enrolled</Badge>}
        </div>

        <h1 className={styles.title}>{title}</h1>
        <p className={styles.description}>{description}</p>

        <div className={styles.actionRow}>
          <Button
            variant="accent"
            size="md"
            onClick={() => navigate(`/map/${slug}`)}
            leftIcon={<Network size={16} />}
          >
            View Concept DAG Map
          </Button>

          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate(`/practice?chapter=${slug}&mode=diagnostic`)}
            leftIcon={<Target size={16} />}
          >
            Take Chapter Diagnostic
          </Button>
        </div>
      </section>

      {/* 2. Layout Grid */}
      <section className={styles.layoutGrid}>
        {/* Resource Sequences */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-lg)', fontWeight: 800 }}>
              Curriculum Resource Packages
            </h3>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
              {resources.length} Core Modules
            </span>
          </div>

          {resources.length === 0 ? (
            <div style={{
              padding: 'var(--space-6)',
              textAlign: 'center',
              border: 'var(--border-hairline)',
              borderRadius: 'var(--radius-micro)',
              color: 'var(--ink-secondary)'
            }}>
              <p>No educational resource packages published for this chapter yet.</p>
            </div>
          ) : (
            <div className={styles.resourceList}>
              {resources.map((res) => (
                <div
                  key={res.id}
                  className={styles.resourceItem}
                  onClick={() => navigate(`/learn/${res.id}`)}
                >
                  <div className={styles.resourceMeta}>
                    <div className={styles.seqBadge}>{res.sequence}</div>
                    <div>
                      <div className={styles.resourceTitle}>{res.title}</div>
                      <div className={styles.resourceSub}>
                        <span>{res.resourceKind?.replace(/_/g, ' ').toUpperCase() || 'LESSON'}</span>
                        <span style={{ margin: '0 6px' }}>•</span>
                        <span><Clock size={11} style={{ verticalAlign: 'middle', marginRight: 2 }} />{res.estimatedMinutes} min</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    {res.isCompleted ? (
                      <Badge variant="olive" size="sm">
                        <CheckCircle2 size={12} style={{ marginRight: 4 }} /> Completed
                      </Badge>
                    ) : (
                      <Button variant="ghost" size="sm" rightIcon={<ChevronRight size={14} />}>
                        Start
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Syllabus Concepts & Prerequisite Foundation Bridge */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Chapter Mastery</CardTitle>
              <Badge variant="olive">{completionPct}%</Badge>
            </CardHeader>
            <CardContent>
              <Progress value={completionPct} showValue color="olive" />
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginTop: 'var(--space-3)' }}>
                Master all 5 resource packages and solve the diagnostic to achieve 100% chapter completion.
              </p>
            </CardContent>
          </Card>

          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Key Syllabus Concepts</CardTitle>
              <Layers size={16} color="#1B4965" />
            </CardHeader>
            <CardContent>
              {concepts.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {concepts.map((concept) => (
                    <div
                      key={concept.id}
                      style={{
                        padding: 'var(--space-2) var(--space-3)',
                        border: 'var(--border-hairline)',
                        borderRadius: 'var(--radius-micro)',
                        fontSize: 'var(--text-xs)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>{concept.title}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--ink-secondary)' }}>
                        Grade {concept.grade}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
                  No individual concepts specified.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default ChapterPage;
