import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Shell from './layout/Shell';
import { RouteLoader } from './fx/fx';
import type { Role } from './api/types';

const Landing = lazy(() => import('./pages/Landing'));
const Auth = lazy(() => import('./pages/Auth'));
const Onboarding = lazy(() => import('./pages/Onboarding'));
const Pipeline = lazy(() => import('./pages/review/Pipeline'));
const ArenaPage = lazy(() => import('./pages/Arena'));
const HomePage = lazy(() => import('./pages/Home'));
const Learn = lazy(() => import('./pages/Learn'));
const Chapter = lazy(() => import('./pages/Chapter'));
const LessonPage = lazy(() => import('./pages/Lesson'));
const Practice = lazy(() => import('./pages/Practice'));
const Progress = lazy(() => import('./pages/Progress'));
const Explore = lazy(() => import('./pages/Explore'));
const MyClasses = lazy(() => import('./pages/MyClasses'));
const ClassRoom = lazy(() => import('./pages/ClassRoom'));
const RevisionPage = lazy(() => import('./pages/Revision'));
const TestStart = lazy(() => import('./pages/tests/Start'));
const TestRun = lazy(() => import('./pages/tests/Run'));
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
  return role === 'teacher' ? '/teacher' : role === 'reviewer' || role === 'admin' ? '/review' : '/home';
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
          <Route path="/home" element={<Guard roles={['student']}><HomePage /></Guard>} />
          <Route path="/today" element={<Navigate to="/home" replace />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/learn/:slug" element={<Chapter />} />
          <Route path="/lesson/:id" element={<LessonPage />} />
          <Route path="/practice" element={<Guard roles={['student']}><Practice /></Guard>} />
          <Route path="/progress" element={<Guard roles={['student']}><Progress /></Guard>} />
          <Route path="/explore" element={<Guard roles={['student']}><Explore /></Guard>} />
          <Route path="/arena" element={<Guard roles={['student']}><ArenaPage /></Guard>} />
          <Route path="/classes" element={<Guard roles={['student']}><MyClasses /></Guard>} />
          <Route path="/classes/:id" element={<Guard roles={['student', 'teacher', 'admin']}><ClassRoom /></Guard>} />
          <Route path="/revision" element={<Guard roles={['student']}><RevisionPage /></Guard>} />
          <Route path="/tests/new" element={<Guard roles={['student']}><TestStart /></Guard>} />
          <Route path="/tests/:id" element={<Guard roles={['student']}><TestRun /></Guard>} />
          <Route path="/map/:slug" element={<MapPage />} />
          <Route path="/ask" element={<Guard roles={['student']}><Ask /></Guard>} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/offline" element={<Offline />} />
          <Route path="/teacher" element={<Guard roles={['teacher', 'admin']}><TeacherClass /></Guard>} />
          <Route path="/teacher/class/:id" element={<Guard roles={['teacher', 'admin']}><TeacherClass /></Guard>} />
          <Route path="/teacher/class/:cid/student/:id" element={<Guard roles={['teacher', 'admin']}><TeacherStudent /></Guard>} />
          <Route path="/teacher/assign" element={<Guard roles={['teacher', 'admin']}><Assign /></Guard>} />
          <Route path="/review" element={<Guard roles={['reviewer', 'admin']}><ReviewQueue /></Guard>} />
          <Route path="/review/pipeline" element={<Guard roles={['reviewer', 'admin']}><Pipeline /></Guard>} />
          <Route path="/review/:id" element={<Guard roles={['reviewer', 'admin']}><ReviewLesson /></Guard>} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
