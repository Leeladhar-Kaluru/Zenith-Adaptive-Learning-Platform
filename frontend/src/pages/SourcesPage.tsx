import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { ShieldCheck } from 'lucide-react';
import { api, IngestionStatus, UserDocument } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ActivityPhase } from '../components/DynamicActivityIndicator';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { useTaxonomy } from '../hooks/useTaxonomy';
import { PlanReviewDialog } from './home/PlanReviewDialog';
import { AddSourcePanel, PipelineStep } from './home/AddSourcePanel';
import { Card, CardHeader, CardTitle, CardContent, Badge, Callout } from '../components/ui';
import styles from './SourcesPage.module.css';

export const SourcesPage: React.FC = () => {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const taxonomy = useTaxonomy(Boolean(user));

  const [materials, setMaterials] = useState<UserDocument[]>([]);

  // Ingestion State
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activityPhase, setActivityPhase] = useState<ActivityPhase>('extracting');
  const [activityDetail, setActivityDetail] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Outline Review Modal State
  const [reviewOutline, setReviewOutline] = useState<IngestionStatus | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [isGeneratingPath, setIsGeneratingPath] = useState(false);
  const [pathGrade, setPathGrade] = useState<string>(user?.grade ? String(user.grade) : '10');
  const [pathSubject, setPathSubject] = useState<string>(user?.subjectsInterested?.[0] || '');

  const pollIntervalRef = useRef<any>(null);
  const uploadRequestRef = useRef<XMLHttpRequest | null>(null);
  const planDialogRef = useRef<HTMLDivElement>(null);

  useDialogFocus(planDialogRef, Boolean(reviewOutline), () => {
    if (!isGeneratingPath) {
      setReviewOutline(null);
      setReviewError(null);
    }
  });

  const fetchMaterials = useCallback(async () => {
    if (!user) return;
    try {
      const docs = await api.listDocuments();
      setMaterials(docs);
    } catch (err: any) {
      console.warn('Could not load materials:', err);
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    void fetchMaterials();
  }, [user, fetchMaterials]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      void handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      void handleFileUpload(e.target.files[0]);
    }
  };

  const pollDocumentStatus = (docId: string, initialFilename: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const status = await api.getDocumentStatus(docId);
        if (status.status === 'awaiting_review') {
          clearInterval(pollIntervalRef.current);
          setIsUploading(false);
          setReviewOutline(status);
          void fetchMaterials();
        } else if (status.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setIsUploading(false);
          setErrorMessage(status.errorMessage || 'Extraction failed. Please try a cleaner PDF or image.');
          void fetchMaterials();
        } else {
          setActivityDetail(status.progressMessage || `Processing ${initialFilename}…`);
        }
      } catch {
        // keep polling
      }
    }, 2500);
  };

  const handleFileUpload = async (file: File) => {
    setErrorMessage(null);
    setIsUploading(true);
    setActivityPhase('extracting');
    setActivityDetail(`Uploading ${file.name}…`);
    try {
      const doc = await api.uploadDocument(file);
      pollDocumentStatus(doc.documentId, file.name);
    } catch (err: any) {
      setIsUploading(false);
      setErrorMessage(err.message || 'Upload failed.');
    }
  };

  const handleCreatePathFromOutline = async () => {
    if (!reviewOutline) return;
    setIsGeneratingPath(true);
    setReviewError(null);
    try {
      await api.createLearningPath({
        documentId: reviewOutline.documentId,
        grade: pathGrade ? Number(pathGrade) : 10,
        subjectId: pathSubject || 'subject-math'
      });
      setReviewOutline(null);
      void fetchMaterials();
    } catch (err: any) {
      setReviewError(err.message || 'Could not generate learning plan.');
    } finally {
      setIsGeneratingPath(false);
    }
  };

  const subjectOptions = useMemo(() => {
    return taxonomy.subjects.map(s => ({ id: s.id, label: s.name }));
  }, [taxonomy.subjects]);

  const pipeline: PipelineStep[] = [
    { id: '1', label: 'Upload' },
    { id: '2', label: 'Extract Text' },
    { id: '3', label: 'Index & Chunk' },
    { id: '4', label: 'Ready for Review' }
  ];

  return (
    <div className={styles.page}>
      {/* Rule 10 Privacy Guarantee Banner */}
      <div className={styles.privacyBanner}>
        <ShieldCheck size={22} className={styles.privacyBannerIcon} />
        <div>
          <div className={styles.privacyBannerTitle}>Rule 10 Privacy Guarantee</div>
          <div className={styles.privacyBannerText}>
            Your uploaded textbooks and private study notes remain strictly confidential. Extraction runs in isolated sandbox environments with per-source rights enforcement. No unauthorized rehosting.
          </div>
        </div>
      </div>

      <div className={styles.headerSection}>
        <span className={styles.headerKicker}>Source & Document Hub</span>
        <h1 className={styles.headerTitle}>Upload Textbooks & Learning Materials</h1>
        <p className={styles.headerDesc}>
          Upload syllabus textbooks (PDF, DOCX, TXT) to generate custom chapter outlines, interactive units, and grounded tutoring references.
        </p>
      </div>

      {errorMessage && (
        <Callout variant="warning" title="Upload Notice">
          {errorMessage}
        </Callout>
      )}

      <div className={styles.grid}>
        <div>
          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Add New Textbook</CardTitle>
            </CardHeader>
            <CardContent>
              <AddSourcePanel
                fileInputRef={fileInputRef}
                isDragging={isDragging}
                isUploading={isUploading}
                showPipelineProgress={isUploading}
                pipeline={pipeline}
                activePipelineIndex={1}
                progressPercent={undefined}
                currentBookFilename={undefined}
                activityPhase={activityPhase}
                activityDetail={activityDetail}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onFileChange={handleFileChange}
                onCancel={() => {
                  uploadRequestRef.current?.abort();
                  if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                  setIsUploading(false);
                }}
              />
            </CardContent>
          </Card>
        </div>

        <div>
          <Card elevation={2}>
            <CardHeader>
              <CardTitle>Uploaded Documents</CardTitle>
              <Badge variant="ultramarine">{materials.length} Files</Badge>
            </CardHeader>
            <CardContent>
              {materials.length === 0 ? (
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ink-secondary)' }}>
                  No custom documents uploaded yet. Upload a file on the left to begin.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  {materials.map((doc) => (
                    <div
                      key={doc.id}
                      style={{
                        padding: 'var(--space-3)',
                        border: 'var(--border-hairline)',
                        borderRadius: 'var(--radius-micro)',
                        backgroundColor: 'var(--surface-paper)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ fontSize: 'var(--text-sm)' }}>{doc.filename}</strong>
                        <Badge
                          variant={doc.status === 'ready' ? 'olive' : doc.status === 'failed' ? 'terracotta' : 'saffron'}
                          size="sm"
                        >
                          {doc.status}
                        </Badge>
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--ink-secondary)', marginTop: '4px' }}>
                        {doc.createdAt ? new Date(doc.createdAt).toLocaleDateString() : 'Recent'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {reviewOutline && (
        <PlanReviewDialog
          outline={reviewOutline}
          reviewError={reviewError}
          isGeneratingPath={isGeneratingPath}
          grade={pathGrade}
          subject={pathSubject}
          subjectOptions={subjectOptions}
          taxonomy={{
            loading: taxonomy.loading,
            error: taxonomy.error,
            retry: taxonomy.retry,
          }}
          dialogRef={planDialogRef}
          onGradeChange={setPathGrade}
          onSubjectChange={setPathSubject}
          onClose={() => {
            if (isGeneratingPath) return;
            setReviewOutline(null);
            setReviewError(null);
          }}
          onBuild={handleCreatePathFromOutline}
        />
      )}
    </div>
  );
};

export default SourcesPage;
