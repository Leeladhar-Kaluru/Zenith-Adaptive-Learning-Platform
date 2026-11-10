import uuid
import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class BktState(Base):
    __tablename__ = "bkt_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    p_know = Column(Float, default=0.25, nullable=False)
    total_opportunities = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    streak = Column(Integer, default=0, nullable=False)
    mastery_band = Column(String(50), default="not_enough_evidence", nullable=False)
    is_gap = Column(Boolean, default=False, nullable=False)
    gap_signal_count = Column(Integer, default=0, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("student_id", "concept_id", name="uq_bkt_state_student_concept"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("p_know", 0.25)
        kwargs.setdefault("total_opportunities", 0)
        kwargs.setdefault("correct_count", 0)
        kwargs.setdefault("streak", 0)
        kwargs.setdefault("mastery_band", "not_enough_evidence")
        kwargs.setdefault("is_gap", False)
        kwargs.setdefault("gap_signal_count", 0)
        super().__init__(**kwargs)


class BktEvent(Base):
    __tablename__ = "bkt_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_number = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    prior_p_know = Column(Float, nullable=False)
    post_p_know = Column(Float, nullable=False)
    attempt_id = Column(UUID(as_uuid=True), nullable=True)
    hint_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("hint_used", False)
        super().__init__(**kwargs)
