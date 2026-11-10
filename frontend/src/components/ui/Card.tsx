import React from 'react';
import styles from './Card.module.css';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevation?: 0 | 1 | 2 | 3;
  pastel?: 'default' | 'parchment' | 'saffron' | 'ultramarine' | 'terracotta' | 'olive' | 'peach';
  interactive?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  elevation = 2,
  pastel = 'default',
  interactive = false,
  className = '',
  ...props
}) => {
  const rootClass = [
    styles.card,
    styles[`elevation${elevation}`],
    styles[pastel],
    interactive ? styles.interactive : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} {...props}>
      {children}
    </div>
  );
};

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}
export const CardHeader: React.FC<CardHeaderProps> = ({ children, className = '', ...props }) => (
  <div className={`${styles.header} ${className}`} {...props}>
    {children}
  </div>
);

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}
export const CardTitle: React.FC<CardTitleProps> = ({ children, className = '', ...props }) => (
  <h3 className={`${styles.title} ${className}`} {...props}>
    {children}
  </h3>
);

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}
export const CardDescription: React.FC<CardDescriptionProps> = ({ children, className = '', ...props }) => (
  <p className={`${styles.description} ${className}`} {...props}>
    {children}
  </p>
);

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}
export const CardContent: React.FC<CardContentProps> = ({ children, className = '', ...props }) => (
  <div className={`${styles.content} ${className}`} {...props}>
    {children}
  </div>
);

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}
export const CardFooter: React.FC<CardFooterProps> = ({ children, className = '', ...props }) => (
  <div className={`${styles.footer} ${className}`} {...props}>
    {children}
  </div>
);
