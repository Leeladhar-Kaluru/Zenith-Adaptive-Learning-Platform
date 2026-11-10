import React from 'react';
import { Link } from 'react-router-dom';
import styles from './Logo.module.css';

export interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  asLink?: boolean;
  to?: string;
  className?: string;
  showSubtitle?: boolean;
}

export const Logo: React.FC<LogoProps> = ({
  size = 'md',
  asLink = true,
  to = '/',
  className = '',
  showSubtitle = true
}) => {
  const content = (
    <div className={`${styles.logo} ${styles[size]} ${className}`}>
      <div className={styles.markWrap} aria-hidden="true">
        <svg viewBox="0 0 100 100" width="100%" height="100%" fill="none">
          <polygon points="54,12 88,46 54,92 20,46" fill="#1E1E1E" />
          <polygon points="50,8 50,42 16,42" fill="#FF9933" stroke="#1E1E1E" strokeWidth="2.5" strokeLinejoin="round" />
          <polygon points="50,8 84,42 50,42" fill="#FEF3C7" stroke="#1E1E1E" strokeWidth="2.5" strokeLinejoin="round" />
          <polygon points="50,42 50,88 16,42" fill="#1B4965" stroke="#1E1E1E" strokeWidth="2.5" strokeLinejoin="round" />
          <polygon points="50,42 84,42 50,88" fill="#C84B31" stroke="#1E1E1E" strokeWidth="2.5" strokeLinejoin="round" />
          <line x1="50" y1="8" x2="50" y2="88" stroke="#1E1E1E" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="16" y1="42" x2="84" y2="42" stroke="#1E1E1E" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>
      <div className={styles.textWrap}>
        <span className={styles.title}>ZENITH</span>
        {showSubtitle && <span className={styles.subtitle}>ADAPTIVE COMPANION</span>}
      </div>
    </div>
  );

  if (asLink) {
    return (
      <Link to={to} style={{ textDecoration: 'none' }}>
        {content}
      </Link>
    );
  }

  return content;
};
