import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, HelpCircle, Edit3, CheckCircle, XCircle, Zap, ArrowRight } from 'lucide-react';
import {
  api,
  PracticeQuestion,
  PracticeSubmitResponse,
  DiagnosticSubmitResponse
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { queuePracticeAttemptOffline } from '../db/indexedDB';
import { Button, Badge, Progress, MathText, Callout } from '../components/ui';
import styles from './PracticePage.module.css';

export const PracticePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const chapterSlug = searchParams.get('chapter') || 'real-numbers';
  const conceptId = searchParams.get('concept') || undefined;
  const isDiagnostic = searchParams.get('mode') === 'diagnostic';

  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [showScratchpad, setShowScratchpad] = useState(false);
  const [scratchNotes, setScratchNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<PracticeSubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Diagnostic mode tracking
  const [diagSessionId, setDiagSessionId] = useState<string | null>(null);
  const [diagResponses, setDiagResponses] = useState<Array<{
    itemIndex: number;
    itemId: string;
    studentResponse: string;
    hintsUsed: number;
    is_correct?: boolean;
  }>>([]);
  const [diagSummary, setDiagSummary] = useState<DiagnosticSubmitResponse | null>(null);

  useEffect(() => {
    let active = true;

    async function initSession() {
      setLoading(true);
      try {
        if (isDiagnostic) {
          const diag = await api.startDiagnosticSession(chapterSlug);
          if (!active) return;
          setDiagSessionId(diag.sessionId);
          const mapped: PracticeQuestion[] = diag.items.map((item) => ({
            questionId: item.itemId,
            conceptId: item.conceptId,
            type: 'multiple_choice',
            prompt: item.prompt,
            options: item.options,
            hints: ['Review the foundational definition of this chapter.'],
            difficulty: item.difficulty
          }));
          setQuestions(mapped);
        } else {
          const sess = await api.createPracticeSession(chapterSlug, conceptId, 5);
          if (!active) return;
          setQuestions(sess.questions);
        }
      } catch (err: any) {
        console.warn('Practice session initialization fallback:', err);
        // Calibrated fallback questions
        if (active) {
          setQuestions([
            {
              questionId: 'cbse-10-real-numbers-q1',
              conceptId: 'cbse-10-math-real-numbers-fta',
              type: 'multiple_choice',
              prompt: 'The prime factorisation of natural number $288$ is:',
              options: ['$2^5 \\times 3^2$', '$2^4 \\times 3^3$', '$2^6 \\times 3^1$', '$2^3 \\times 3^4$'],
              hints: ['Divide 288 repeatedly by 2: $288 = 2 \\times 144 = 2^2 \\times 72$…'],
              difficulty: 'medium'
            },
            {
              questionId: 'cbse-10-real-numbers-q2',
              conceptId: 'cbse-10-math-real-numbers-hcf-lcm',
              type: 'multiple_choice',
              prompt: 'Given that $\\text{HCF}(96, 404) = 4$, the $\\text{LCM}(96, 404)$ is:',
              options: ['$9696$', '$4848$', '$9898$', '$4040$'],
              hints: ['Use the formula $\\text{LCM}(a, b) = \\frac{a \\times b}{\\text{HCF}(a, b)}$.'],
              difficulty: 'easy'
            },
            {
              questionId: 'cbse-10-real-numbers-q3',
              conceptId: 'cbse-10-math-real-numbers-irrationality',
              type: 'multiple_choice',
              prompt: 'Which of the following numbers is an irrational number?',
              options: ['$\\sqrt{7}$', '$\\sqrt{4}$', '$\\sqrt{9}$', '$\\frac{22}{7}$'],
              hints: ['If $p$ is a prime number, $\\sqrt{p}$ is always irrational.'],
              difficulty: 'easy'
            }
          ]);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void initSession();

    return () => {
      active = false;
    };
  }, [chapterSlug, conceptId, isDiagnostic]);

  const currentQ = questions[currentIndex];

  const handleSelectOption = (opt: string) => {
    if (submitResult) return;
    setSelectedOption(opt);
  };

  const handleHintClick = () => {
    setShowHint(true);
    setHintsUsed((prev) => prev + 1);
  };

  const handleSubmit = async () => {
    if (!selectedOption || !currentQ || isSubmitting) return;
    setIsSubmitting(true);

    const idempotencyKey = `practice_${currentQ.questionId}_${Date.now()}`;

    try {
      if (isDiagnostic) {
        // Record in diagnostic list without client-side grading bias
        const updatedResponses = [
          ...diagResponses,
          {
            itemIndex: currentIndex,
            itemId: currentQ.questionId,
            studentResponse: selectedOption,
            hintsUsed: hintsUsed,
          }
        ];
        setDiagResponses(updatedResponses);

        // Informative assessment state (allows moving to next probe)
        setSubmitResult({
          questionId: currentQ.questionId,
          conceptId: currentQ.conceptId,
          isCorrect: true,
          feedback: 'Answer recorded! Diagnostic mastery will be evaluated upon completing the assessment.',
          explanation: '',
          pKnow: 0.25,
          masteryBand: 'assessing',
          isGap: false,
          rewards: {
            awarded: false,
            xpAwarded: 0,
            coinsAwarded: 0,
            totalXp: 0,
            currentStreak: 0
          }
        });
      } else {
        const res = await api.submitPracticeAttempt({
          questionId: currentQ.questionId,
          conceptId: currentQ.conceptId,
          response: selectedOption,
          hintLevel: showHint ? 1 : 0,
          hintsUsed: hintsUsed > 0 ? [`hint_${hintsUsed}`] : [],
          elapsedSeconds: 20,
          syncIdempotencyKey: idempotencyKey
        });
        setSubmitResult(res);
      }
    } catch (err) {
      console.warn('Network submission failed, queueing offline attempt:', err);
      // Offline fallback
      if (user) {
        await queuePracticeAttemptOffline({
          clientAttemptId: idempotencyKey,
          ownerId: user.id,
          questionId: currentQ.questionId,
          conceptId: currentQ.conceptId,
          response: selectedOption,
          hintLevel: showHint ? 1 : 0,
          hintsUsed: [],
          elapsedSeconds: 15
        });
      }
      setSubmitResult({
        questionId: currentQ.questionId,
        conceptId: currentQ.conceptId,
        isCorrect: false,
        feedback: 'Answer saved offline! Evaluation and knowledge tracing will sync upon reconnection.',
        explanation: 'Work saved locally.',
        pKnow: 0.25,
        masteryBand: 'queued',
        isGap: false,
        rewards: {
          awarded: false,
          xpAwarded: 0,
          coinsAwarded: 0,
          totalXp: 0,
          currentStreak: 0
        }
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = async () => {
    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOption(null);
      setSubmitResult(null);
      setShowHint(false);
      setHintsUsed(0);
    } else if (isDiagnostic && diagSessionId) {
      // Diagnostic complete - submit entire battery to backend for server-side evaluation
      setIsSubmitting(true);
      try {
        const finalResponses = diagResponses.map((r) => ({
          itemIndex: r.itemIndex,
          itemId: r.itemId,
          studentResponse: r.studentResponse,
          hintsUsed: r.hintsUsed,
        }));
        const summary = await api.submitDiagnostic(diagSessionId, finalResponses);
        setDiagSummary(summary);
      } catch (err: any) {
        console.warn('Diagnostic finalize error:', err);
        setDiagSummary({
          sessionId: diagSessionId,
          totalProbes: questions.length,
          correctCount: 0,
          accuracyPct: 0,
          masteryUpdates: {},
          gapSummary: {
            confirmedGaps: [],
            gapCount: 0
          },
          recommendedPractice: {
            conceptId: '',
            conceptTitle: 'Review Prerequisite Concepts',
            reason: 'Review foundational material from this chapter.'
          },
          rewards: {
            xpAwarded: 0,
            coinsAwarded: 0,
            totalXp: 0
          }
        });
      } finally {
        setIsSubmitting(false);
      }
    } else {
      // Practice complete
      navigate(`/chapter/${chapterSlug}`);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        Calibrating Practice Arena…
      </div>
    );
  }

  // Diagnostic Summary Screen
  if (diagSummary) {
    return (
      <div className={styles.page}>
        <div className={styles.summaryCard}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <Badge variant="olive" size="md">Diagnostic Complete</Badge>
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '32px', fontWeight: 800 }}>
            Assessment Summary
          </h1>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-6)' }}>
            <div>
              <div style={{ fontSize: '36px', fontFamily: 'var(--font-mono)', fontWeight: 800 }}>
                {diagSummary.accuracyPct}%
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', textTransform: 'uppercase' }}>
                Accuracy ({diagSummary.correctCount}/{diagSummary.totalProbes})
              </div>
            </div>
            <div>
              <div style={{ fontSize: '36px', fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#D97706' }}>
                +{diagSummary.rewards.xpAwarded} XP
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', textTransform: 'uppercase' }}>
                Earned Reward
              </div>
            </div>
          </div>

          <Callout variant="info" title="Recommended Next Focus">
            <div>
              <strong>{diagSummary.recommendedPractice.conceptTitle}</strong>
              <p style={{ marginTop: '4px' }}>{diagSummary.recommendedPractice.reason}</p>
            </div>
          </Callout>

          <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-3)' }}>
            <Button
              variant="primary"
              size="lg"
              onClick={() =>
                navigate(
                  `/practice?chapter=${chapterSlug}&concept=${diagSummary.recommendedPractice.conceptId}`
                )
              }
              rightIcon={<ArrowRight size={18} />}
            >
              Practice Weakest Topic
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate(`/map/${chapterSlug}`)}
            >
              View Updated Concept DAG
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!currentQ) {
    return (
      <div className={styles.page}>
        <p>No questions found in this session.</p>
        <Button variant="outline" onClick={() => navigate(-1)}>Go Back</Button>
      </div>
    );
  }

  const optionLetters = ['A', 'B', 'C', 'D', 'E'];

  return (
    <div className={styles.page}>
      {/* 1. Header & Progress */}
      <div className={styles.topBar}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/chapter/${chapterSlug}`)}
          leftIcon={<ArrowLeft size={14} />}
        >
          Exit Practice
        </Button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <Badge variant={isDiagnostic ? 'terracotta' : 'saffron'}>
            {isDiagnostic ? 'Diagnostic Assessment' : 'Adaptive Arena'}
          </Badge>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>
            Question {currentIndex + 1} of {questions.length}
          </span>
        </div>
      </div>

      <Progress
        value={((currentIndex + 1) / questions.length) * 100}
        color="saffron"
      />

      {/* 2. Interactive Arena Card */}
      <section className={styles.arenaCard}>
        <div className={styles.questionHeader}>
          <Badge variant="neutral">{currentQ.difficulty || 'Medium'} Difficulty</Badge>
          <div className={styles.headerTools}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowScratchpad(!showScratchpad)}
              leftIcon={<Edit3 size={14} />}
            >
              Scratchpad
            </Button>
            {currentQ.hints && currentQ.hints.length > 0 && !submitResult && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleHintClick}
                leftIcon={<HelpCircle size={14} />}
              >
                Hint ({hintsUsed})
              </Button>
            )}
          </div>
        </div>

        {/* Scratchpad */}
        {showScratchpad && (
          <div className={styles.scratchpad}>
            <textarea
              className={styles.scratchpadTextarea}
              placeholder="Rough calculations & scratchpad notes (stays on your screen during the quiz)…"
              value={scratchNotes}
              onChange={(e) => setScratchNotes(e.target.value)}
            />
          </div>
        )}

        {/* Question Prompt */}
        <div className={styles.promptBox}>
          <MathText content={currentQ.prompt} />
        </div>

        {/* Hint Reveal */}
        {showHint && currentQ.hints?.[0] && (
          <Callout variant="tip" title="Hint for this problem">
            <MathText content={currentQ.hints[0]} />
          </Callout>
        )}

        {/* Options List */}
        <div className={styles.optionsList}>
          {currentQ.options.map((opt, i) => {
            const isSelected = selectedOption === opt;
            let optStyle = styles.optionButton;
            if (isSelected) optStyle += ` ${styles.optionSelected}`;

            if (submitResult && !isDiagnostic) {
              if (submitResult.isCorrect && isSelected) optStyle += ` ${styles.optionCorrect}`;
              else if (isSelected && !submitResult.isCorrect) optStyle += ` ${styles.optionIncorrect}`;
            }

            return (
              <button
                key={i}
                className={optStyle}
                onClick={() => handleSelectOption(opt)}
                disabled={Boolean(submitResult)}
              >
                <div className={styles.optionIndexBadge}>{optionLetters[i]}</div>
                <div style={{ flex: 1 }}>
                  <MathText content={opt} />
                </div>
              </button>
            );
          })}
        </div>

        {/* Feedback Banner after submission */}
        {submitResult && (
          <div
            className={`${styles.feedbackBanner} ${
              submitResult.isCorrect ? styles.feedbackCorrect : styles.feedbackIncorrect
            }`}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                {submitResult.isCorrect ? (
                  <CheckCircle size={20} color="#166534" />
                ) : (
                  <XCircle size={20} color="#C84B31" />
                )}
                <strong style={{ fontSize: 'var(--text-base)' }}>
                  {submitResult.isCorrect ? 'Correct!' : 'Keep Going!'}
                </strong>
              </div>

              {submitResult.rewards && submitResult.rewards.awarded && (
                <div className={styles.xpToast}>
                  <Zap size={14} /> +{submitResult.rewards.xpAwarded} XP
                </div>
              )}
            </div>

            <p style={{ fontSize: 'var(--text-sm)' }}>{submitResult.feedback}</p>
            {submitResult.explanation && (
              <div style={{ fontSize: 'var(--text-xs)', marginTop: '4px', opacity: 0.9 }}>
                <MathText content={submitResult.explanation} />
              </div>
            )}

            <div style={{ marginTop: 'var(--space-2)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Badge variant="neutral" size="sm">
                BKT Mastery $P(\text{'{'}know{'}'})$: {Math.round(submitResult.pKnow * 100)}%
              </Badge>
              <Badge variant={submitResult.isGap ? 'terracotta' : 'olive'} size="sm">
                {submitResult.masteryBand.replace(/_/g, ' ').toUpperCase()}
              </Badge>
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
          {!submitResult ? (
            <Button
              variant="primary"
              size="lg"
              disabled={!selectedOption || isSubmitting}
              onClick={handleSubmit}
            >
              {isSubmitting ? 'Checking…' : 'Submit Answer'}
            </Button>
          ) : (
            <Button
              variant="primary"
              size="lg"
              onClick={handleNext}
              rightIcon={<ArrowRight size={18} />}
            >
              {currentIndex + 1 < questions.length ? 'Next Question' : 'Complete Assessment'}
            </Button>
          )}
        </div>
      </section>
    </div>
  );
};

export default PracticePage;
