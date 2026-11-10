import React from 'react';
import { BookOpen, Info, AlertTriangle, Lightbulb } from 'lucide-react';
import styles from './Callout.module.css';

export interface CalloutProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'definition' | 'info' | 'warning' | 'tip';
  title?: string;
  icon?: React.ReactNode;
}

export const Callout: React.FC<CalloutProps> = ({
  children,
  variant = 'info',
  title,
  icon,
  className = '',
  ...props
}) => {
  const defaultIcons = {
    definition: <BookOpen size={18} />,
    info: <Info size={18} />,
    warning: <AlertTriangle size={18} />,
    tip: <Lightbulb size={18} />
  };

  const defaultTitles = {
    definition: 'Definition',
    info: 'Key Concept',
    warning: 'Common Misconception',
    tip: 'Pro Tip'
  };

  const resolvedIcon = icon !== undefined ? icon : defaultIcons[variant];
  const resolvedTitle = title !== undefined ? title : defaultTitles[variant];

  return (
    <div className={`${styles.callout} ${styles[variant]} ${className}`} {...props}>
      {resolvedIcon && <div className={styles.iconWrap}>{resolvedIcon}</div>}
      <div className={styles.content}>
        {resolvedTitle && <div className={styles.title}>{resolvedTitle}</div>}
        <div className={styles.body}>{children}</div>
      </div>
    </div>
  );
};
