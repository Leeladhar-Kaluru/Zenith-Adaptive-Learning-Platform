import uuid
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class TutorThread(Base):
    __tablename__ = "tutor_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="SET NULL"), nullable=True, index=True)
    concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("tutor_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # student | assistant | system
    content = Column(Text, nullable=False)
    citations_json = Column(JSON, nullable=True)
    status = Column(String(50), default="delivered", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "delivered")
        super().__init__(**kwargs)
