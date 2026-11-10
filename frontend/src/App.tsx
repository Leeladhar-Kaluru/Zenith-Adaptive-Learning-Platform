import React, { ReactNode, Suspense, lazy } from 'react';
import { Navigate, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { AuthGate } from './components/AuthGate';
import { ErrorBoundary } from './components/ErrorBoundary';
import styles from './App.module.css';

// Lazy-loaded pages for optimal chunking
const HomePage = lazy(() => import('./pages/HomePage'));
const ExplorePage = lazy(() => import('./pages/ExplorePage'));
const ChapterPage = lazy(() => import('./pages/ChapterPage'));
const LessonReaderPage = lazy(() => import('./pages/LessonReaderPage'));
const PracticePage = lazy(() => import('./pages/PracticePage'));
const LearningMapPage = lazy(() => import('./pages/LearningMapPage'));
const AchievementsPage = lazy(() => import('./pages/AchievementsPage'));
const AskZenithPage = lazy(() => import('./pages/AskZenithPage'));
const SourcesPage = lazy(() => import('./pages/SourcesPage'));
const OfflineLibraryPage = lazy(() => import('./pages/OfflineLibraryPage').then(m => ({ default: m.OfflineLibraryPage })));
const DoubtQueuePage = lazy(() => import('./pages/DoubtQueuePage').then(m => ({ default: m.DoubtQueuePage })));
const StudentDashboardPage = lazy(() => import('./pages/StudentDashboardPage').then(m => ({ default: m.StudentDashboardPage })));
const TeacherDashboardPage = lazy(() => import('./pages/TeacherDashboardPage').then(m => ({ default: m.TeacherDashboardPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

const StudentOnly: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (user?.role === 'teacher') return <Navigate to="/teacher" replace />;
  return <>{children}</>;
};

const PageSkeleton: React.FC = () => (
  <div style={{ padding: 'var(--space-8)', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--ink-secondary)' }}>
    Loading ZENITH desk…
  </div>
);

const AppContent: React.FC = () => {
  const { isLoading, sessionError, retrySession, logout } = useAuth();

  if (isLoading) {
    return (
      <div className={styles.shell}>
        <main id="main-content" className={styles.main} tabIndex={-1}>
          <p className={styles.appLoading}>Loading ZENITH…</p>
        </main>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className={styles.shell}>
        <main id="main-content" className={styles.main} tabIndex={-1}>
          <section className={styles.sessionError} role="alert">
            <span className={styles.sessionKicker}>Connection paused</span>
            <h1>Your desk is still here</h1>
            <p>{sessionError}</p>
            <div className={styles.sessionActions}>
              <button type="button" onClick={() => void retrySession()}>Try again</button>
              <button type="button" className={styles.sessionSignOut} onClick={() => void logout()}>
                Sign out
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <AppLayout>
      <ErrorBoundary>
        <Suspense fallback={<PageSkeleton />}>
          <Routes>
            <Route path="/" element={<StudentOnly><HomePage /></StudentOnly>} />
            <Route path="/explore" element={<StudentOnly><ExplorePage /></StudentOnly>} />
            <Route path="/chapter/:slug" element={<StudentOnly><ChapterPage /></StudentOnly>} />
            <Route path="/learn/:lessonId" element={<StudentOnly><LessonReaderPage /></StudentOnly>} />
            <Route path="/lesson/:lessonId" element={<StudentOnly><LessonReaderPage /></StudentOnly>} />
            <Route path="/practice" element={<StudentOnly><PracticePage /></StudentOnly>} />
            <Route path="/map" element={<StudentOnly><LearningMapPage /></StudentOnly>} />
            <Route path="/map/:slug" element={<StudentOnly><LearningMapPage /></StudentOnly>} />
            <Route path="/achievements" element={<StudentOnly><AchievementsPage /></StudentOnly>} />
            <Route path="/ask" element={<StudentOnly><AskZenithPage /></StudentOnly>} />
            <Route path="/sources" element={<StudentOnly><SourcesPage /></StudentOnly>} />
            <Route
              path="/dashboard"
              element={
                <AuthGate>
                  <StudentOnly><StudentDashboardPage /></StudentOnly>
                </AuthGate>
              }
            />
            <Route
              path="/library"
              element={
                <AuthGate>
                  <StudentOnly><OfflineLibraryPage /></StudentOnly>
                </AuthGate>
              }
            />
            <Route
              path="/doubts"
              element={
                <AuthGate>
                  <StudentOnly><DoubtQueuePage /></StudentOnly>
                </AuthGate>
              }
            />
            <Route
              path="/teacher"
              element={
                <AuthGate teacherOnly>
                  <TeacherDashboardPage />
                </AuthGate>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </AppLayout>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
