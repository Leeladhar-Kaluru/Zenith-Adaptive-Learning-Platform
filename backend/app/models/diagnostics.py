import uuid
import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="in_progress", nullable=False)
    total_items = Column(Integer, default=8, nullable=False)
    completed_items = Column(Integer, default=0, nullable=False)
    score_pct = Column(Float, nullable=True)
    summary_json = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "in_progress")
        kwargs.setdefault("total_items", 8)
        kwargs.setdefault("completed_items", 0)
        super().__init__(**kwargs)


class DiagnosticItem(Base):
    __tablename__ = "diagnostic_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    item_index = Column(Integer, nullable=False)
    concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    is_prerequisite_probe = Column(Boolean, default=False, nullable=False)
    question_json = Column(JSON, nullable=False)
    student_response = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_prerequisite_probe", False)
        super().__init__(**kwargs)
