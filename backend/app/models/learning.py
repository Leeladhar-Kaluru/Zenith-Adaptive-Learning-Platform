from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk

BANDS = ("unassessed", "learning", "secure", "gap_suspected", "gap_confirmed")


class EvidenceEvent(Base):
    """Immutable raw evidence. Mastery is always derived from these rows, never edited by hand."""
    __tablename__ = "evidence_events"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="SET NULL"))
    client_event_id = Column(String(64), nullable=False)
    context = Column(String(12), nullable=False)
    response = Column(JSONB, nullable=False)
    correct = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    hints_used = Column(Integer, nullable=False, default=0)
    ms = Column(Integer, nullable=False, default=0)
    attempt_no = Column(Integer, nullable=False, default=1)
    concepts = Column(JSONB, nullable=False, default=list)       # [{id, w, p_before, p_after}]
    misconception_id = Column(UUID(as_uuid=True), ForeignKey("misconceptions.id"))
    param_version = Column(String(20), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = now_col()
    __table_args__ = (
        UniqueConstraint("student_id", "client_event_id", name="uq_evidence_client_event"),
        CheckConstraint("context in ('learn_check','solve','test','probe')", name="ck_evidence_context"),
        Index("ix_evidence_student_time", "student_id", "occurred_at"),
        Index("ix_evidence_student_item", "student_id", "item_id"),
    )


class ConceptState(Base):
    __tablename__ = "concept_states"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    p_known = Column(Float, nullable=False)
    n_obs = Column(Integer, nullable=False, default=0)
    n_correct = Column(Integer, nullable=False, default=0)
    streak = Column(Integer, nullable=False, default=0)
    last_obs_at = Column(DateTime(timezone=True))
    status = Column(String(16), nullable=False, default="unassessed")
    param_version = Column(String(20), nullable=False)
    updated_at = now_col()
    __table_args__ = (CheckConstraint("p_known > 0 and p_known < 1", name="ck_state_p"),)


class LearnerRating(Base):
    __tablename__ = "learner_ratings"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    subject_id = Column(String(30), ForeignKey("subjects.id"), primary_key=True)
    theta = Column(Float, nullable=False, default=0.0)
    n = Column(Integer, nullable=False, default=0)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(12), nullable=False, default="started")
    last_block = Column(Integer, nullable=False, default=0)
    started_at = now_col()
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status in ('started','completed')", name="ck_progress_status"),)


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(12), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"))
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="SET NULL"))
    concept_ids = Column(JSONB, nullable=False, default=list)
    item_ids = Column(JSONB, nullable=False, default=list)
    time_limit_s = Column(Integer)
    status = Column(String(12), nullable=False, default="active")
    started_at = now_col()
    submitted_at = Column(DateTime(timezone=True))
    summary = Column(JSONB)
    __table_args__ = (
        CheckConstraint("kind in ('diagnostic','chapter_test','topic_test','revision','practice')", name="ck_session_kind"),
        CheckConstraint("status in ('active','submitted','expired')", name="ck_session_status"),
    )


class Recommendation(Base):
    """What ZENITH suggested and why, kept for audit and for measuring whether suggestions helped."""
    __tablename__ = "recommendations"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)
    concept_id = Column(String(120))
    payload = Column(JSONB, nullable=False, default=dict)
    reason = Column(JSONB, nullable=False, default=dict)
    model_version = Column(String(20), nullable=False)
    created_at = now_col()


class RevisionSchedule(Base):
    __tablename__ = "revision_schedule"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    due_at = Column(DateTime(timezone=True), nullable=False)
    interval_days = Column(Integer, nullable=False, default=1)
    reps = Column(Integer, nullable=False, default=0)
    last_reviewed_at = Column(DateTime(timezone=True))


class Intervention(Base):
    __tablename__ = "interventions"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(String(120), ForeignKey("concepts.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True))
    kind = Column(String(16), nullable=False)
    pre_p = Column(Float, nullable=False)
    post_p = Column(Float)
    status = Column(String(8), nullable=False, default="open")
    started_at = now_col()
    closed_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status in ('open','closed')", name="ck_intervention_status"),)


class ConceptLevel(Base):
    """Where this student is on the 1-5 difficulty ladder for a concept, and why it last moved."""
    __tablename__ = "concept_levels"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    level = Column(Integer, nullable=False, default=1)
    streak_up = Column(Integer, nullable=False, default=0)
    streak_down = Column(Integer, nullable=False, default=0)
    reason = Column(Text, nullable=False, default="")
    updated_at = now_col()
    __table_args__ = (CheckConstraint("level between 1 and 5", name="ck_level_range"),)


INTERACTION_KINDS = ("lesson_open", "section_view", "dwell", "hint_open", "answer_change", "sim_change", "sim_reset", "skip", "tutor_open")


class InteractionEvent(Base):
    """Every move a student makes while learning: reading, hints, answer edits, simulation changes."""
    __tablename__ = "interaction_events"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    client_event_id = Column(String(64), nullable=False)
    kind = Column(String(16), nullable=False)
    target_type = Column(String(16), nullable=False)
    target_id = Column(String(120), nullable=False)
    value = Column(JSONB, nullable=False, default=dict)
    ms = Column(Integer, nullable=False, default=0)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = now_col()
    __table_args__ = (
        UniqueConstraint("student_id", "client_event_id", name="uq_interaction_client_event"),
        CheckConstraint("kind in (" + ",".join(f"'{k}'" for k in INTERACTION_KINDS) + ")", name="ck_interaction_kind"),
        Index("ix_interaction_student_time", "student_id", "occurred_at"),
        Index("ix_interaction_target", "student_id", "target_id"),
    )
