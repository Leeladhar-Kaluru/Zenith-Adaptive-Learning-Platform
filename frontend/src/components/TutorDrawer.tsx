import React, { useState } from 'react';
import { Sparkles, X, Send, BookOpen } from 'lucide-react';
import { api, TutorCitation, TutorMessageResponse } from '../services/api';
import { Button, MathText } from './ui';

export interface TutorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  chapterSlug?: string;
  resourceKey?: string;
  conceptId?: string;
}

export const TutorDrawer: React.FC<TutorDrawerProps> = ({
  isOpen,
  onClose,
  chapterSlug,
  resourceKey,
  conceptId
}) => {
  const [input, setInput] = useState('');
  const [conversation, setConversation] = useState<Array<{ sender: 'student' | 'tutor'; text: string; citations?: TutorCitation[] }>>([
    {
      sender: 'tutor',
      text: 'Ask any question about this lesson or concept. I will guide you with grounded curriculum steps.'
    }
  ]);
  const [busy, setBusy] = useState(false);

  if (!isOpen) return null;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;

    const userText = input.trim();
    setInput('');
    setConversation((prev) => [...prev, { sender: 'student', text: userText }]);
    setBusy(true);

    try {
      const res: TutorMessageResponse = await api.sendTutorMessage({
        message: userText,
        chapterSlug,
        resourceKey,
        conceptId
      });
      setConversation((prev) => [
        ...prev,
        { sender: 'tutor', text: res.reply, citations: res.citations }
      ]);
    } catch {
      setConversation((prev) => [
        ...prev,
        {
          sender: 'tutor',
          text: 'To approach this problem, remember the Fundamental Theorem of Arithmetic. What are the prime factors of the numbers you are examining?'
        }
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(30, 30, 30, 0.45)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '420px',
          maxWidth: '100%',
          height: '100%',
          backgroundColor: 'var(--surface-paper)',
          borderLeft: 'var(--border-heavy)',
          boxShadow: '-4px 0px 0px var(--ink-charcoal)',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <header
          style={{
            padding: 'var(--space-4) var(--space-5)',
            borderBottom: 'var(--border-heavy)',
            backgroundColor: 'var(--pastel-saffron)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Sparkles size={18} color="#1E1E1E" />
            <strong style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-base)' }}>
              Ask ZENITH Socratic Tutor
            </strong>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={16} />
          </Button>
        </header>

        <div style={{ flex: 1, padding: 'var(--space-5)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {conversation.map((msg, idx) => (
            <div
              key={idx}
              style={{
                alignSelf: msg.sender === 'student' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                padding: 'var(--space-3) var(--space-4)',
                borderRadius: 'var(--radius-micro)',
                border: msg.sender === 'student' ? 'none' : 'var(--border-medium)',
                backgroundColor: msg.sender === 'student' ? 'var(--ink-charcoal)' : '#FFFFFF',
                color: msg.sender === 'student' ? '#FFFFFF' : 'var(--ink-charcoal)',
                fontSize: 'var(--text-sm)',
                lineHeight: 1.5,
                boxShadow: 'var(--shadow-brutal-xs)'
              }}
            >
              <MathText content={msg.text} />
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ marginTop: 'var(--space-2)', fontSize: '11px', opacity: 0.85 }}>
                  <BookOpen size={11} style={{ verticalAlign: 'middle', marginRight: 3 }} />
                  {msg.citations[0].source}
                </div>
              )}
            </div>
          ))}
        </div>

        <form
          onSubmit={handleSend}
          style={{
            padding: 'var(--space-4)',
            borderTop: 'var(--border-heavy)',
            display: 'flex',
            gap: 'var(--space-2)'
          }}
        >
          <input
            style={{
              flex: 1,
              height: '42px',
              padding: '0 var(--space-3)',
              border: 'var(--border-heavy)',
              borderRadius: 'var(--radius-micro)',
              fontSize: 'var(--text-sm)'
            }}
            placeholder="Type your question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="submit" variant="primary" size="md" disabled={busy || !input.trim()}>
            <Send size={15} />
          </Button>
        </form>
      </div>
    </div>
  );
};
