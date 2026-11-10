import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Shell from './layout/Shell';
import { RouteLoader } from './fx/fx';
import type { Role } from './api/types';

const Landing = lazy(() => import('./pages/Landing'));
const Auth = lazy(() => import('./pages/Auth'));
const Onboarding = lazy(() => import('./pages/Onboarding'));
const TodayPage = lazy(() => import('./pages/Today'));
const Learn = lazy(() => import('./pages/Learn'));
const Chapter = lazy(() => import('./pages/Chapter'));
const LessonPage = lazy(() => import('./pages/Lesson'));
const Practice = lazy(() => import('./pages/Practice'));
const ClimbPage = lazy(() => import('./pages/Climb'));
const MapPage = lazy(() => import('./pages/ConceptMap'));
const Ask = lazy(() => import('./pages/Ask'));
const Settings = lazy(() => import('./pages/Settings'));
const Offline = lazy(() => import('./pages/Offline'));
const TeacherClass = lazy(() => import('./pages/teacher/ClassView'));
const TeacherStudent = lazy(() => import('./pages/teacher/StudentView'));
const Assign = lazy(() => import('./pages/teacher/Assign'));
const ReviewQueue = lazy(() => import('./pages/review/Queue'));
const ReviewLesson = lazy(() => import('./pages/review/Lesson'));
const NotFound = lazy(() => import('./pages/NotFound'));

function homeFor(role?: Role) {
  return role === 'teacher' ? '/teacher' : role === 'reviewer' || role === 'admin' ? '/review' : '/today';
}

function Guard({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { profile, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <RouteLoader label="Opening ZENITH" />;
  if (!profile) return <Navigate to="/signin" state={{ from: loc.pathname }} replace />;
  if (!profile.onboardingCompleted && loc.pathname !== '/onboarding') return <Navigate to="/onboarding" replace />;
  if (roles && !roles.includes(profile.role)) return <Navigate to={homeFor(profile.role)} replace />;
  return <>{children}</>;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { profile, loading } = useAuth();
  if (loading) return <RouteLoader label="Opening ZENITH" />;
  if (profile) return <Navigate to={homeFor(profile.role)} replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<PublicOnly><Landing /></PublicOnly>} />
        <Route path="/signin" element={<PublicOnly><Auth mode="signin" /></PublicOnly>} />
        <Route path="/signup" element={<PublicOnly><Auth mode="signup" /></PublicOnly>} />
        <Route path="/onboarding" element={<Guard><Onboarding /></Guard>} />
        <Route element={<Guard><Shell /></Guard>}>
          <Route path="/today" element={<Guard roles={['student']}><TodayPage /></Guard>} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/learn/:slug" element={<Chapter />} />
          <Route path="/lesson/:id" element={<LessonPage />} />
          <Route path="/practice" element={<Guard roles={['student']}><Practice /></Guard>} />
          <Route path="/climb" element={<Guard roles={['student']}><ClimbPage /></Guard>} />
          <Route path="/map/:slug" element={<MapPage />} />
          <Route path="/ask" element={<Guard roles={['student']}><Ask /></Guard>} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/offline" element={<Offline />} />
          <Route path="/teacher" element={<Guard roles={['teacher', 'admin']}><TeacherClass /></Guard>} />
          <Route path="/teacher/class/:id" element={<Guard roles={['teacher', 'admin']}><TeacherClass /></Guard>} />
          <Route path="/teacher/student/:id" element={<Guard roles={['teacher', 'admin']}><TeacherStudent /></Guard>} />
          <Route path="/teacher/assign" element={<Guard roles={['teacher', 'admin']}><Assign /></Guard>} />
          <Route path="/review" element={<Guard roles={['teacher', 'reviewer', 'admin']}><ReviewQueue /></Guard>} />
          <Route path="/review/:id" element={<Guard roles={['teacher', 'reviewer', 'admin']}><ReviewLesson /></Guard>} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
