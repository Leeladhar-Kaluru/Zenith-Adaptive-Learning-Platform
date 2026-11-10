import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Clock, Layers, ArrowRight } from 'lucide-react';
import { api, LibraryCatalogueResponse } from '../services/api';
import { Button, Card, CardHeader, CardTitle, CardContent, CardFooter, Badge, Progress } from '../components/ui';
import styles from './ExplorePage.module.css';

const AVAILABLE_GRADES = [6, 7, 8, 9, 10];
const AVAILABLE_SUBJECTS = [
  { id: 'subject-math', label: 'Mathematics', code: 'MATH' },
  { id: 'subject-science', label: 'Science', code: 'SCI' },
];

export const ExplorePage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedGrade, setSelectedGrade] = useState<number>(10);
  const [selectedSubject, setSelectedSubject] = useState<string>('subject-math');
  const [catalogue, setCatalogue] = useState<LibraryCatalogueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [enrollingSlug, setEnrollingSlug] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);

    async function loadCatalogue() {
      try {
        const res = await api.getLibraryCatalogue(selectedGrade, selectedSubject);
        if (active) setCatalogue(res);
      } catch (err) {
        console.warn('Failed to load curriculum catalogue:', err);
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadCatalogue();

    return () => {
      active = false;
    };
  }, [selectedGrade, selectedSubject]);

  const handleEnroll = async (slug: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEnrollingSlug(slug);
    try {
      await api.enrollChapter(slug);
      const updated = await api.getLibraryCatalogue(selectedGrade, selectedSubject);
      setCatalogue(updated);
    } catch (err) {
      console.warn('Enrollment error:', err);
    } finally {
      setEnrollingSlug(null);
    }
  };

  // Rule 2 Compliance: Use real catalogue chapters only, NO hardcoded fake data
  const chapters = catalogue?.chapters ?? [];
  const totalChapters = chapters.length;
  const totalPackages = chapters.reduce((sum, ch) => sum + (ch.resourceCount || 0), 0);
  const totalConcepts = chapters.reduce((sum, ch) => sum + (ch.conceptCount || 0), 0);
  const currentSubjectObj = AVAILABLE_SUBJECTS.find((s) => s.id === selectedSubject) || AVAILABLE_SUBJECTS[0];

  return (
    <div className={styles.page}>
      {/* 1. Header Banner */}
      <section className={styles.headerCard}>
        <span className={styles.breadcrumb}>
          Curriculum Library / Class {selectedGrade} {currentSubjectObj.label} (CBSE)
        </span>
        <h1 className={styles.title}>
          Class {selectedGrade} {currentSubjectObj.label}
        </h1>
        <div className={styles.metaRow}>
          <Badge variant="ultramarine">CBSE Curriculum</Badge>
          <Badge variant="saffron">{totalChapters} {totalChapters === 1 ? 'Chapter' : 'Chapters'}</Badge>
          <Badge variant="olive">{totalPackages} Resource Packages</Badge>
          <Badge variant="charcoal">{totalConcepts} Calibrated Concepts</Badge>
        </div>
      </section>

      {/* 2. Interactive Class & Subject Navigation (Canvas Classes Inspired) */}
      <section className={styles.filterBar}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', width: '100%' }}>
          {/* Class Selectors */}
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--ink-secondary)', minWidth: 60 }}>
              CLASS:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              {AVAILABLE_GRADES.map((grade) => {
                const isActive = grade === selectedGrade;
                return (
                  <button
                    key={grade}
                    onClick={() => setSelectedGrade(grade)}
                    style={{
                      padding: '6px 14px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-micro)',
                      border: 'var(--border-medium)',
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'var(--accent-saffron)' : 'var(--surface-paper)',
                      color: 'var(--ink-charcoal)',
                      boxShadow: isActive ? 'var(--shadow-brutal-sm)' : 'none',
                      transform: isActive ? 'translate(-1px, -1px)' : 'none',
                      transition: 'all 0.1s ease',
                    }}
                  >
                    Class {grade}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Subject Selectors */}
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--ink-secondary)', minWidth: 60 }}>
              SUBJECT:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              {AVAILABLE_SUBJECTS.map((subj) => {
                const isActive = subj.id === selectedSubject;
                return (
                  <button
                    key={subj.id}
                    onClick={() => setSelectedSubject(subj.id)}
                    style={{
                      padding: '6px 14px',
                      fontFamily: 'var(--font-display)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-micro)',
                      border: 'var(--border-medium)',
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'var(--accent-ultramarine)' : 'var(--surface-paper)',
                      color: isActive ? '#FFFFFF' : 'var(--ink-charcoal)',
                      boxShadow: isActive ? 'var(--shadow-brutal-sm)' : 'none',
                      transform: isActive ? 'translate(-1px, -1px)' : 'none',
                      transition: 'all 0.1s ease',
                    }}
                  >
                    {subj.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* 3. Loading State */}
      {loading ? (
        <div style={{ padding: 'var(--space-10)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
          Loading Class {selectedGrade} {currentSubjectObj.label} Curriculum…
        </div>
      ) : chapters.length === 0 ? (
        <div
          style={{
            padding: 'var(--space-10)',
            textAlign: 'center',
            background: 'var(--surface-paper)',
            border: 'var(--border-medium)',
            borderRadius: 'var(--radius-sm)',
            boxShadow: 'var(--shadow-brutal-sm)',
          }}
        >
          <p
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-lg)',
              fontWeight: 700,
              marginBottom: 'var(--space-2)',
            }}
          >
            No syllabus chapters published for Class {selectedGrade} {currentSubjectObj.label} yet
          </p>
          <p style={{ color: 'var(--ink-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
            Content is actively being calibrated. Switch to another class or subject to explore ready chapters.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-3)' }}>
            <Button variant="outline" size="sm" onClick={() => setSelectedGrade(10)}>
              View Class 10
            </Button>
            <Button variant="outline" size="sm" onClick={() => setSelectedSubject('subject-math')}>
              View Mathematics
            </Button>
          </div>
        </div>
      ) : (
        <section className={styles.chapterGrid}>
          {chapters.map((ch) => (
            <Card
              key={ch.slug}
              elevation={2}
              interactive
              className={styles.chapterCard}
              onClick={() => navigate(`/chapter/${ch.slug}`)}
            >
              <CardHeader>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <Badge variant="saffron">Chapter {ch.chapterNumber}</Badge>
                    {ch.isEnrolled && <Badge variant="olive">Enrolled</Badge>}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/map/${ch.slug}`);
                    }}
                  >
                    <Layers size={14} style={{ marginRight: 4 }} /> Concept DAG
                  </Button>
                </div>
                <CardTitle style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-lg)' }}>
                  {ch.title}
                </CardTitle>
              </CardHeader>

              <CardContent>
                <p
                  style={{
                    color: 'var(--ink-secondary)',
                    fontSize: 'var(--text-sm)',
                    lineHeight: 1.5,
                    marginBottom: 'var(--space-3)',
                  }}
                >
                  {ch.description}
                </p>

                {/* Canvas Classes Inspired Resource Pillars */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: 'var(--space-3)' }}>
                  <span style={{ fontSize: '11px', background: '#FEF3C7', border: '1px solid #18181B', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    📖 Notes
                  </span>
                  <span style={{ fontSize: '11px', background: '#DBEAFE', border: '1px solid #18181B', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    💡 Worked Examples
                  </span>
                  <span style={{ fontSize: '11px', background: '#D1FAE5', border: '1px solid #18181B', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    ⚡ Formula Sheet
                  </span>
                  <span style={{ fontSize: '11px', background: '#FCE7F3', border: '1px solid #18181B', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    🎯 Practice MCQs
                  </span>
                  <span style={{ fontSize: '11px', background: '#E0E7FF', border: '1px solid #18181B', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    🧭 Diagnostic
                  </span>
                </div>

                <div className={styles.chapterMetaList}>
                  <span>
                    <BookOpen size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    {ch.resourceCount} modules
                  </span>
                  <span>•</span>
                  <span>
                    <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    {ch.estimatedMinutes} mins
                  </span>
                  <span>•</span>
                  <span>
                    <Layers size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    {ch.conceptCount} concepts
                  </span>
                </div>

                {ch.isEnrolled && (
                  <div style={{ marginTop: 'var(--space-2)' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: 'var(--text-xs)',
                        marginBottom: 4,
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      <span>Progress</span>
                      <span>{ch.completionPct}%</span>
                    </div>
                    <Progress value={ch.completionPct} color="olive" />
                  </div>
                )}
              </CardContent>

              <CardFooter style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <Button
                  variant="primary"
                  size="sm"
                  style={{ flex: 1 }}
                  rightIcon={<ArrowRight size={14} />}
                  onClick={() => navigate(`/chapter/${ch.slug}`)}
                >
                  Explore Modules
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/practice?chapter=${ch.slug}&mode=diagnostic`);
                  }}
                >
                  Take Diagnostic
                </Button>

                {!ch.isEnrolled && (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={enrollingSlug === ch.slug}
                    onClick={(e) => handleEnroll(ch.slug, e)}
                  >
                    {enrollingSlug === ch.slug ? 'Enrolling…' : 'Enroll'}
                  </Button>
                )}
              </CardFooter>
            </Card>
          ))}
        </section>
      )}
    </div>
  );
};

export default ExplorePage;
