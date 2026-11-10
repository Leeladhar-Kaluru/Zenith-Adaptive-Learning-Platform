import React from 'react';
import styles from './Progress.module.css';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number; // 0 to 100
  steps?: number; // If set, renders segmented progress
  currentStep?: number;
  label?: string;
  showValue?: boolean;
  color?: 'saffron' | 'ultramarine' | 'olive' | 'terracotta';
}

export const Progress: React.FC<ProgressProps> = ({
  value = 0,
  steps,
  currentStep = 0,
  label,
  showValue = false,
  color = 'saffron',
  className = '',
  ...props
}) => {
  const clampedValue = Math.min(100, Math.max(0, value));

  if (steps && steps > 0) {
    return (
      <div className={`${styles.wrapper} ${className}`} {...props}>
        {(label || showValue) && (
          <div className={styles.header}>
            {label && <span className={styles.label}>{label}</span>}
            {showValue && <span className={styles.value}>{currentStep}/{steps}</span>}
          </div>
        )}
        <div className={styles.segmentsContainer}>
          {Array.from({ length: steps }).map((_, index) => {
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;
            return (
              <div
                key={index}
                className={`${styles.segment} ${isCompleted ? styles.segmentCompleted : ''} ${isCurrent ? styles.segmentCurrent : ''}`}
                title={`Step ${index + 1}`}
              />
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.wrapper} ${styles[color]} ${className}`} {...props}>
      {(label || showValue) && (
        <div className={styles.header}>
          {label && <span className={styles.label}>{label}</span>}
          {showValue && <span className={styles.value}>{Math.round(clampedValue)}%</span>}
        </div>
      )}
      <div className={styles.track}>
        <div className={styles.bar} style={{ width: `${clampedValue}%` }} />
      </div>
    </div>
  );
};
