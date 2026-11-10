import React, { Component, ErrorInfo, ReactNode } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import styles from './MathText.module.css';

export interface MathTextProps {
  content?: string;
  className?: string;
  inline?: boolean;
}

interface MathErrorBoundaryProps {
  children: ReactNode;
  fallbackMath: string;
  isDisplay?: boolean;
}

interface MathErrorBoundaryState {
  hasError: boolean;
}

/**
 * Dedicated Math Error Boundary to isolate rendering errors in individual mathematical expressions.
 */
export class MathErrorBoundary extends Component<MathErrorBoundaryProps, MathErrorBoundaryState> {
  public state: MathErrorBoundaryState = { hasError: false };

  public static getDerivedStateFromError(): MathErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn('MathText KaTeX rendering caught error:', error, info);
  }

  public render() {
    if (this.state.hasError) {
      const Tag = this.props.isDisplay ? 'div' : 'span';
      return (
        <Tag className={styles.fallbackMath} title="KaTeX rendering fallback">
          {this.props.fallbackMath}
        </Tag>
      );
    }
    return this.props.children;
  }
}

/**
 * Safely renders a LaTeX formula into HTML using KaTeX.
 * Resolves via npm-bundled KaTeX or window.katex (CDN), with throwOnError set to false.
 */
function renderLatexToHtml(latex: string, displayMode: boolean): { html: string; error?: string } {
  try {
    // Check bundled katex or window.katex
    const engine = katex || (typeof window !== 'undefined' ? (window as any).katex : null);
    if (engine && typeof engine.renderToString === 'function') {
      const html = engine.renderToString(latex, {
        displayMode,
        throwOnError: false,
        errorColor: '#B91C1C',
        strict: false,
        trust: false,
        output: 'htmlAndMathml'
      });
      return { html };
    }
    return { html: '', error: 'KaTeX library not loaded' };
  } catch (err: any) {
    return { html: '', error: err?.message || 'Formula render failed' };
  }
}

/**
 * Pure math atom component wrapped with MathErrorBoundary
 */
const MathFormula: React.FC<{ rawMath: string; isDisplay: boolean }> = ({ rawMath, isDisplay }) => {
  const { html, error } = renderLatexToHtml(rawMath, isDisplay);

  if (error || !html) {
    const Tag = isDisplay ? 'div' : 'span';
    return (
      <Tag className={styles.fallbackMath} title={error || 'LaTeX'}>
        {rawMath}
      </Tag>
    );
  }

  if (isDisplay) {
    return (
      <div
        className={styles.displayMath}
        role="math"
        aria-label={rawMath}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  return (
    <span
      className={styles.inlineMath}
      role="math"
      aria-label={rawMath}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

export const MathText: React.FC<MathTextProps> = ({
  content = '',
  className = '',
  inline: isInline = false
}) => {
  if (!content) return null;

  // Split on block math $$...$$ and inline math $...$
  const parts = content.split(/(\$\$[\s\S]+?\$\$|\$[^\$\n]+?\$)/g);

  return (
    <span className={`${styles.mathContainer} ${isInline ? styles.inlineContainer : ''} ${className}`}>
      {parts.map((part, index) => {
        // Block math: $$ ... $$
        if (part.startsWith('$$') && part.endsWith('$$') && part.length >= 4) {
          const rawMath = part.slice(2, -2).trim();
          return (
            <MathErrorBoundary key={index} fallbackMath={rawMath} isDisplay={true}>
              <MathFormula rawMath={rawMath} isDisplay={true} />
            </MathErrorBoundary>
          );
        }

        // Inline math: $ ... $
        if (part.startsWith('$') && part.endsWith('$') && part.length >= 2) {
          const rawMath = part.slice(1, -1).trim();
          return (
            <MathErrorBoundary key={index} fallbackMath={rawMath} isDisplay={false}>
              <MathFormula rawMath={rawMath} isDisplay={false} />
            </MathErrorBoundary>
          );
        }

        // Plain text content
        return <React.Fragment key={index}>{part}</React.Fragment>;
      })}
    </span>
  );
};

export const MathRenderer = MathText;
export default MathText;
