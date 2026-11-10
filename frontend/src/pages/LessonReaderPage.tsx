import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Check, Sparkles, Clock, ChevronRight, HelpCircle } from 'lucide-react';
import { api, ResourcePackageResponse } from '../services/api';
import { saveLessonOffline, getOfflineLesson } from '../db/indexedDB';
import { useAuth } from '../context/AuthContext';
import { Button, Badge, Callout, MathText } from '../components/ui';
import styles from './LessonReaderPage.module.css';

export const LessonReaderPage: React.FC = () => {
  const { lessonId = '' } = useParams<{ lessonId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [resource, setResource] = useState<ResourcePackageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [revealedSteps, setRevealedSteps] = useState<Record<number, number>>({});
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  const [showHints, setShowHints] = useState<Record<string, boolean>>({});
  const [isSavedOffline, setIsSavedOffline] = useState(false);
  const [savingOffline, setSavingOffline] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadResource() {
      if (!lessonId) return;
      try {
        // 1. Try offline cache first
        if (user?.id) {
          const cached = await getOfflineLesson(user.id, lessonId);
          if (cached && active) {
            setIsSavedOffline(true);
            const cachedResource = (
              cached.packageData?.package
                ? cached.packageData
                : cached.packageData?.content?.package
                ? cached.packageData.content
                : null
            ) as ResourcePackageResponse | null;

            if (cachedResource && cachedResource.package) {
              setResource(cachedResource);
              setLoading(false);
              return;
            }
          }
        }

        // 2. Query resource package API
        const res = await api.getResource(lessonId);
        if (active) {
          setResource(res);
        }
      } catch (err: any) {
        if (active) {
          console.warn('Failed to load lesson resource:', err);
          setResource(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadResource();

    return () => {
      active = false;
    };
  }, [lessonId, user]);

  const handleSaveOffline = async () => {
    if (!resource || !user?.id) return;
    setSavingOffline(true);
    try {
      await saveLessonOffline({
        ...resource,
        lessonId: resource.id || lessonId,
        pathId: 'curriculum-library',
        title: resource.package?.title || resource.title,
        grade: resource.package?.grade || 10,
        subjectId: resource.package?.subjectId || 'subject-math',
        sequence: resource.sequence || 1,
        content: resource,
        package: resource.package,
      }, user.id);
      setIsSavedOffline(true);
    } catch (err) {
      console.warn('Offline save failed:', err);
    } finally {
      setSavingOffline(false);
    }
  };

  const toggleStep = (exIndex: number, totalSteps: number) => {
    setRevealedSteps((prev) => {
      const current = prev[exIndex] || 0;
      const next = current < totalSteps ? current + 1 : current;
      return { ...prev, [exIndex]: next };
    });
  };

  const handleSelectAnswer = (qId: string, optIndex: number) => {
    setSelectedAnswers((prev) => ({ ...prev, [qId]: optIndex }));
  };

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        Loading Lesson Resource…
      </div>
    );
  }

  const pkg = resource?.package;
  if (!resource || !pkg) {
    return (
      <div className={styles.readerContainer}>
        <div className={styles.topBar}>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(-1)}
            leftIcon={<ArrowLeft size={14} />}
          >
            Back to Chapter
          </Button>
        </div>
        <Callout
          variant="warning"
          title="Lesson Resource Unavailable"
        >
          This lesson package could not be retrieved from the server or offline cache. Please check your network connection and try again.
        </Callout>
      </div>
    );
  }

  const title = pkg?.title || 'Interactive Concept Lesson';
  const estimatedMinutes = pkg?.estimatedMinutes || 20;

  return (
    <div className={styles.readerContainer}>
      {/* 1. Top Navigation Bar */}
      <div className={styles.topBar}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(-1)}
          leftIcon={<ArrowLeft size={14} />}
        >
          Back to Chapter
        </Button>

        <div className={styles.topBarActions}>
          <Button
            variant={isSavedOffline ? 'secondary' : 'outline'}
            size="sm"
            onClick={handleSaveOffline}
            disabled={savingOffline || isSavedOffline}
            leftIcon={isSavedOffline ? <Check size={14} color="#166534" /> : <Download size={14} />}
          >
            {isSavedOffline ? 'Saved Offline' : savingOffline ? 'Saving…' : 'Save for Offline'}
          </Button>

          <Button
            variant="accent"
            size="sm"
            onClick={() => navigate(`/ask?resource=${encodeURIComponent(lessonId)}`)}
            leftIcon={<Sparkles size={14} />}
          >
            Ask Socratic Tutor
          </Button>
        </div>
      </div>

      {/* 2. Lesson Header Card */}
      <section className={styles.readerHeader}>
        <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
          <Badge variant="saffron">Class 10 CBSE Math</Badge>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Clock size={12} /> {estimatedMinutes} mins read
          </span>
        </div>

        <h1 className={styles.lessonTitle}>{title}</h1>

        {pkg?.objectives && pkg.objectives.length > 0 && (
          <div className={styles.objectivesBox}>
            <h4>Learning Objectives</h4>
            <ul className={styles.objectivesList}>
              {pkg.objectives.map((obj, i) => (
                <li key={i}>{obj}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* 3. Structured Content Blocks */}
      <section className={styles.contentWell}>
        {pkg?.blocks?.map((block, idx) => {
          if (block.kind === 'definition') {
            return (
              <Callout key={idx} variant="definition" title={block.heading || 'Definition'}>
                <MathText content={block.content} />
              </Callout>
            );
          }
          if (block.kind === 'callout') {
            return (
              <Callout key={idx} variant="tip" title={block.heading || 'Key Tip'}>
                <MathText content={block.content} />
              </Callout>
            );
          }
          if (block.kind === 'summary') {
            return (
              <Callout key={idx} variant="info" title={block.heading || 'Summary & Checklist'}>
                <MathText content={block.content} />
              </Callout>
            );
          }

          return (
            <article key={idx} className={styles.blockSection}>
              {block.heading && <h3 className={styles.blockHeading}>{block.heading}</h3>}
              <div className={styles.blockContent}>
                <MathText content={block.content} />
              </div>
            </article>
          );
        })}
      </section>

      {/* 4. Worked Examples with Step-by-Step Collapsible Reveals */}
      {pkg?.workedExamples && pkg.workedExamples.length > 0 && (
        <section>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-xl)', fontWeight: 800, marginBottom: 'var(--space-4)' }}>
            Step-by-Step Worked Examples
          </h2>

          {pkg.workedExamples.map((ex, exIdx) => {
            const revealed = revealedSteps[exIdx] || 0;
            const totalSteps = ex.steps.length;
            const isAllRevealed = revealed >= totalSteps;

            return (
              <div key={exIdx} className={styles.workedExampleCard}>
                <div className={styles.workedExampleHead}>
                  <strong style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-sm)', color: 'var(--accent-ultramarine)' }}>
                    Worked Example #{exIdx + 1}
                  </strong>
                  <Badge variant="ultramarine" size="sm">
                    {revealed} / {totalSteps} Steps Revealed
                  </Badge>
                </div>

                <div className={styles.workedExamplePrompt}>
                  <MathText content={ex.prompt} />
                </div>

                <div className={styles.stepsContainer}>
                  {ex.steps.slice(0, revealed).map((step, sIdx) => (
                    <div key={sIdx} className={styles.stepItem}>
                      <MathText content={step} />
                    </div>
                  ))}

                  {!isAllRevealed && (
                    <div>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => toggleStep(exIdx, totalSteps)}
                        rightIcon={<ChevronRight size={14} />}
                      >
                        {revealed === 0 ? 'Show Step 1' : `Show Step ${revealed + 1}`}
                      </Button>
                    </div>
                  )}

                  {isAllRevealed && ex.answer && (
                    <div className={styles.finalAnswer}>
                      <span>Final Solution: </span>
                      <MathText content={ex.answer} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* 5. Embedded Practice Checkpoints */}
      {pkg?.practice && pkg.practice.length > 0 && (
        <section>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-xl)', fontWeight: 800, marginBottom: 'var(--space-4)' }}>
            Practice Checkpoints
          </h2>

          {pkg.practice.map((q, qIdx) => {
            const selectedOpt = selectedAnswers[q.questionId];
            const hasAnswered = selectedOpt !== undefined;
            const isCorrect = selectedOpt === 0; // Canonical first index or verified
            const showingHint = showHints[q.questionId];

            return (
              <div key={q.questionId || qIdx} className={styles.practiceCheckpoint}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                  <Badge variant="saffron">Checkpoint #{qIdx + 1}</Badge>
                  {q.hints && q.hints.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setShowHints((prev) => ({ ...prev, [q.questionId]: !showingHint }))
                      }
                      leftIcon={<HelpCircle size={14} />}
                    >
                      {showingHint ? 'Hide Hint' : 'Need a Hint?'}
                    </Button>
                  )}
                </div>

                <p style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  <MathText content={q.prompt} />
                </p>

                {showingHint && q.hints?.[0] && (
                  <Callout variant="tip" title="Hint">
                    <MathText content={q.hints[0]} />
                  </Callout>
                )}

                <div>
                  {q.options?.map((opt, oIdx) => {
                    let optClass = styles.optionBtn;
                    if (hasAnswered) {
                      if (oIdx === 0) optClass += ` ${styles.optionCorrect}`;
                      else if (selectedOpt === oIdx) optClass += ` ${styles.optionIncorrect}`;
                    }

                    return (
                      <button
                        key={oIdx}
                        className={optClass}
                        onClick={() => handleSelectAnswer(q.questionId, oIdx)}
                        disabled={hasAnswered}
                      >
                        <MathText content={opt} />
                      </button>
                    );
                  })}
                </div>

                {hasAnswered && (
                  <div style={{ marginTop: 'var(--space-4)' }}>
                    <Callout
                      variant={isCorrect ? 'tip' : 'warning'}
                      title={isCorrect ? 'Correct! High Five' : 'Review the Concept'}
                    >
                      <MathText content={q.feedback || 'Review the properties above for details.'} />
                    </Callout>
                  </div>
                )}
              </div>
            );
          })}
        </section>
      )}

      {/* Floating Ask Socratic Tutor Drawer Trigger */}
      <div className={styles.floatingTutorBtn}>
        <Button
          variant="accent"
          size="lg"
          onClick={() => navigate(`/ask?resource=${encodeURIComponent(lessonId)}`)}
          leftIcon={<Sparkles size={18} />}
        >
          Ask ZENITH Tutor
        </Button>
      </div>
    </div>
  );
};

export default LessonReaderPage;
