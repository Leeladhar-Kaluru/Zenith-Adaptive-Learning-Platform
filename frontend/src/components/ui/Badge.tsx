import React from 'react';
import styles from './Badge.module.css';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'saffron' | 'terracotta' | 'ultramarine' | 'olive' | 'charcoal' | 'neutral';
  shape?: 'tag' | 'pill';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'saffron',
  shape = 'tag',
  size = 'md',
  icon,
  className = '',
  ...props
}) => {
  const rootClass = [
    styles.badge,
    styles[variant],
    styles[shape],
    styles[size],
    className
  ].filter(Boolean).join(' ');

  return (
    <span className={rootClass} {...props}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </span>
  );
};
