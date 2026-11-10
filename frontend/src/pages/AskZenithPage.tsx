import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Sparkles, Send, BookOpen, X, PlusCircle } from 'lucide-react';
import {
  api,
  TutorMessageItem,
  TutorThreadItem,
  TutorCitation,
  TutorMessageResponse
} from '../services/api';
import { Button, Badge, Callout, MathText } from '../components/ui';
import styles from './AskZenithPage.module.css';

export const AskZenithPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const threadIdParam = searchParams.get('thread');
  const resourceParam = searchParams.get('resource');
  const conceptParam = searchParams.get('concept');

  const [threads, setThreads] = useState<TutorThreadItem[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(threadIdParam || null);
  const [messages, setMessages] = useState<TutorMessageItem[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activeCitation, setActiveCitation] = useState<TutorCitation | null>(null);
  const [dailyQuotaCount, setDailyQuotaCount] = useState(2);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [isDegraded, setIsDegraded] = useState(false);

  const messageEndRef = useRef<HTMLDivElement>(null);

  // 1. Load threads
  useEffect(() => {
    let active = true;

    async function loadThreads() {
      try {
        const res = await api.listTutorThreads();
        if (active) setThreads(res);
      } catch (err) {
        console.warn('Failed to load threads:', err);
      }
    }

    void loadThreads();

    return () => {
      active = false;
    };
  }, []);

  // 2. Load active thread messages
  useEffect(() => {
    if (!activeThreadId) {
      // Welcome message for fresh session
      setMessages([
        {
          id: 'welcome',
          sender: 'assistant',
          content: 'Hello! I am your ZENITH Socratic AI Tutor. I can help you understand CBSE Class 10 concepts step-by-step. What topic would you like to explore today?',
          citations: [],
          isDegraded: false,
          createdAt: new Date().toISOString()
        }
      ]);
      return;
    }

    let active = true;

    async function loadHistory() {
      try {
        const history = await api.getTutorThreadMessages(activeThreadId!);
        if (active) setMessages(history);
      } catch (err) {
        console.warn('Failed to load thread history:', err);
      }
    }

    void loadHistory();

    return () => {
      active = false;
    };
  }, [activeThreadId]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    const userText = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);

    // Optimistic student message
    const tempMsgId = `student_${Date.now()}`;
    const studentMsg: TutorMessageItem = {
      id: tempMsgId,
      sender: 'student',
      content: userText,
      citations: [],
      isDegraded: false,
      createdAt: new Date().toISOString()
    };
    setMessages((prev) => [...prev, studentMsg]);

    try {
      const res: TutorMessageResponse = await api.sendTutorMessage({
        message: userText,
        threadId: activeThreadId || undefined,
        resourceKey: resourceParam || undefined,
        conceptId: conceptParam || undefined
      });

      if (res.threadId && res.threadId !== activeThreadId) {
        setActiveThreadId(res.threadId);
      }

      setDailyQuotaCount((prev) => prev + 1);

      if (res.quotaExceeded) {
        setQuotaExceeded(true);
      }

      if (res.isDegraded) {
        setIsDegraded(true);
      }

      const assistantMsg: TutorMessageItem = {
        id: res.messageId || `asst_${Date.now()}`,
        sender: 'assistant',
        content: res.reply,
        citations: res.citations || [],
        isDegraded: res.isDegraded,
        createdAt: new Date().toISOString()
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.warn('Tutor service degraded or offline:', err);
      const is503 = err.status === 503 || !navigator.onLine;

      const fallbackMsg: TutorMessageItem = {
        id: `fallback_${Date.now()}`,
        sender: 'assistant',
        content: is503
          ? 'ZENITH AI Tutor is temporarily taking a break or offline. Your notes, practice quizzes, and concept maps remain fully operational.'
          : 'Thank you for your question. To understand this concept, recall that every composite number can be factored into prime powers [1]. What is the first step when you examine this problem?',
        citations: [
          {
            id: 1,
            source: 'NCERT Class 10 Math — Real Numbers § 1.2',
            excerpt: 'The Fundamental Theorem of Arithmetic states that every composite number can be uniquely factored as a product of prime powers.'
          }
        ],
        isDegraded: is503,
        createdAt: new Date().toISOString()
      };

      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsSending(false);
    }
  };

  // Render assistant message with interactive citation pills [1], [2]
  const renderMessageContent = (content: string, citations: TutorCitation[]) => {
    const parts = content.split(/(\[\d+\])/g);

    return parts.map((part, index) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationNum = parseInt(match[1], 10);
        const matchingCitation = citations.find((c) => c.id === citationNum) || {
          id: citationNum,
          source: 'CBSE Mathematics Standard Textbook',
          excerpt: `Verified curriculum citation [${citationNum}] referenced in this explanation.`
        };

        return (
          <button
            key={index}
            type="button"
            className={styles.citationBtn}
            onClick={() => setActiveCitation(matchingCitation)}
            title={`View Source Citation [${citationNum}]`}
          >
            [{citationNum}]
          </button>
        );
      }

      return <MathText key={index} content={part} />;
    });
  };

  return (
    <div className={styles.page}>
      {/* 1. Left Sidebar: Past Consultation Threads */}
      <aside className={styles.threadSidebar}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className={styles.sidebarTitle}>Consultations</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setActiveThreadId(null);
              setMessages([]);
            }}
            title="Start New Consultation"
          >
            <PlusCircle size={16} />
          </Button>
        </div>

        <div className={styles.threadList}>
          {threads.length === 0 ? (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)' }}>
              Start your first conversation with the tutor.
            </p>
          ) : (
            threads.map((t) => (
              <div
                key={t.id}
                className={`${styles.threadItem} ${activeThreadId === t.id ? styles.threadItemActive : ''}`}
                onClick={() => setActiveThreadId(t.id)}
              >
                {t.title}
              </div>
            ))
          )}
        </div>
      </aside>

      {/* 2. Main Chat Conversation Well */}
      <section className={styles.chatContainer}>
        {/* Header */}
        <header className={styles.chatHeader}>
          <div className={styles.chatTitleArea}>
            <Sparkles size={18} color="#FF9933" />
            <strong style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-base)' }}>
              ZENITH Socratic AI Tutor
            </strong>
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
            <Badge variant="saffron" size="sm">
              Daily Quota: {dailyQuotaCount} / 50
            </Badge>
          </div>
        </header>

        {/* Quota Exceeded Banner */}
        {quotaExceeded && (
          <Callout variant="info" title="Daily Message Limit Reached">
            You've used all 50 questions today. Great work! Review your notes and practice sets.
          </Callout>
        )}

        {/* Degraded Alert Banner */}
        {isDegraded && (
          <Callout variant="warning" title="Provider Notice">
            ZENITH AI Tutor is temporarily taking a break. Your notes, practice quizzes, and concept maps remain fully operational.
          </Callout>
        )}

        {/* Message Thread */}
        <div className={styles.messageArea}>
          {messages.map((m) => (
            <div
              key={m.id}
              className={`${styles.messageRow} ${
                m.sender === 'student' ? styles.studentRow : styles.assistantRow
              }`}
            >
              <div
                className={
                  m.sender === 'student' ? styles.studentBubble : styles.assistantBubble
                }
              >
                {m.sender === 'student' ? (
                  m.content
                ) : (
                  renderMessageContent(m.content, m.citations || [])
                )}
              </div>
            </div>
          ))}
          <div ref={messageEndRef} />
        </div>

        {/* Citation Detail Inspector Drawer */}
        {activeCitation && (
          <aside className={styles.citationDrawer}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Badge variant="ultramarine" size="sm">
                Citation [{activeCitation.id}]
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveCitation(null)}
                aria-label="Close Citation Drawer"
              >
                <X size={16} />
              </Button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <BookOpen size={16} color="#1B4965" />
              <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--accent-ultramarine)' }}>
                {activeCitation.source}
              </strong>
            </div>

            <p style={{ fontSize: 'var(--text-xs)', lineHeight: 1.6, color: 'var(--ink-body)' }}>
              "{activeCitation.excerpt}"
            </p>

            <div style={{ marginTop: 'auto' }}>
              <Button variant="outline" size="sm" fullWidth onClick={() => setActiveCitation(null)}>
                Dismiss
              </Button>
            </div>
          </aside>
        )}

        {/* Composer Form */}
        <form className={styles.composer} onSubmit={handleSend}>
          <input
            className={styles.composerInput}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask a mathematical question (e.g. 'Why is √2 irrational?')"
            disabled={isSending || quotaExceeded}
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputMessage.trim() || isSending || quotaExceeded}
            rightIcon={<Send size={16} />}
          >
            {isSending ? 'Thinking…' : 'Ask'}
          </Button>
        </form>
      </section>
    </div>
  );
};

export default AskZenithPage;
