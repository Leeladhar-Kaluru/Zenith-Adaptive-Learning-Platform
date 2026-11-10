import React from 'react';
import { Navigation } from '../Navigation';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { AskZenith } from '../AskZenith';
import { OnboardingTour } from '../OnboardingTour';
import { useAuth } from '../../context/AuthContext';
import styles from './AppLayout.module.css';

export interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { isTourOpen, closeTour } = useAuth();

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skipLink}>
        Skip to content
      </a>

      <Navigation />

      <div className={styles.deskArea}>
        <Header />
        <main id="main-content" className={styles.mainContent} tabIndex={-1}>
          {children}
        </main>
      </div>

      <BottomNav />
      <AskZenith />
      <OnboardingTour isOpen={isTourOpen} onClose={closeTour} />
    </div>
  );
};
