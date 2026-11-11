from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk


class Notification(Base):
    """An in-app message for one person: new lessons, a battle ready, revision due. Links point inside the app only."""
    __tablename__ = "notifications"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(24), nullable=False)
    title = Column(String(120), nullable=False)
    body = Column(String(300), nullable=False, default="")
    link = Column(String(200))
    dedupe_key = Column(String(120))
    created_at = now_col()
    read_at = Column(DateTime(timezone=True))
    __table_args__ = (Index("ix_notifications_user_time", "user_id", "created_at"), Index("uq_notification_dedupe", "user_id", "dedupe_key", unique=True))


class IngestJob(Base):
    """One unit of pipeline work. `request` jobs are what students ask for; the runner turns them into `import` and `draft` work."""
    __tablename__ = "ingest_jobs"
    id = uuid_pk()
    kind = Column(String(10), nullable=False)
    status = Column(String(10), nullable=False, default="queued")
    grade = Column(Integer)
    subject_id = Column(String(30), ForeignKey("subjects.id"))
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="SET NULL"))
    topic = Column(String(120))
    demand = Column(Integer, nullable=False, default=1)           # how many different students asked
    asset_id = Column(UUID(as_uuid=True), ForeignKey("source_assets.id", ondelete="SET NULL"))
    result = Column(JSONB, nullable=False, default=dict)
    error = Column(String(300))
    attempts = Column(Integer, nullable=False, default=0)
    created_at = now_col()
    updated_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("kind in ('request','import','draft')", name="ck_job_kind"),
        CheckConstraint("status in ('queued','running','done','failed','blocked')", name="ck_job_status"),
        Index("ix_ingest_jobs_status", "status", "kind"),
    )


class JobRequester(Base):
    """Who asked for a request job, so demand counts each person once and pressing the button again changes nothing."""
    __tablename__ = "ingest_job_requesters"
    job_id = Column(UUID(as_uuid=True), ForeignKey("ingest_jobs.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    created_at = now_col()


class LessonDraft(Base):
    """A machine-assisted lesson draft waiting for a person. Never shown to students; a reviewer exports it into the content tree."""
    __tablename__ = "lesson_drafts"
    id = uuid_pk()
    job_id = Column(UUID(as_uuid=True), ForeignKey("ingest_jobs.id", ondelete="SET NULL"))
    asset_id = Column(UUID(as_uuid=True), ForeignKey("source_assets.id", ondelete="SET NULL"))
    grade = Column(Integer, nullable=False)
    subject_id = Column(String(30), ForeignKey("subjects.id"), nullable=False)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="SET NULL"))
    slug = Column(String(80), nullable=False)
    title = Column(String(160), nullable=False)
    lesson = Column(JSONB, nullable=False)
    scorecard = Column(JSONB, nullable=False, default=dict)
    score = Column(Float, nullable=False, default=0.0)
    verdict = Column(String(10), nullable=False, default="review")
    status = Column(String(12), nullable=False, default="ready")
    model = Column(String(60))
    created_at = now_col()
    __table_args__ = (
        CheckConstraint("verdict in ('review','rejected')", name="ck_draft_verdict"),
        CheckConstraint("status in ('ready','exported','dismissed')", name="ck_draft_status"),
    )
