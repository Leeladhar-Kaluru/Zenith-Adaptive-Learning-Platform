import uuid
import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(100), primary_key=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    grade = Column(Integer, nullable=False, index=True)
    subject_id = Column(String(50), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    keywords = Column(JSON, nullable=True)
    p_l0 = Column(Float, default=0.25, nullable=False)
    p_t = Column(Float, default=0.15, nullable=False)
    p_g = Column(Float, default=0.20, nullable=False)
    p_s = Column(Float, default=0.10, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("p_l0", 0.25)
        kwargs.setdefault("p_t", 0.15)
        kwargs.setdefault("p_g", 0.20)
        kwargs.setdefault("p_s", 0.10)
        super().__init__(**kwargs)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    to_concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship = Column(String(50), default="prerequisite", nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("from_concept_id", "to_concept_id", name="uq_concept_edge_from_to"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("relationship", "prerequisite")
        kwargs.setdefault("weight", 1.0)
        super().__init__(**kwargs)


class ConceptChapter(Base):
    __tablename__ = "concept_chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id = Column(String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_order = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("concept_id", "path_id", name="uq_concept_chapter_concept_path"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("chapter_order", 1)
        super().__init__(**kwargs)


class LibraryEnrollment(Base):
    __tablename__ = "library_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="active", nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "path_id", name="uq_library_enrollment_student_path"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "active")
        super().__init__(**kwargs)


class ResourceProgress(Base):
    __tablename__ = "resource_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    path_lesson_id = Column(UUID(as_uuid=True), ForeignKey("path_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="not_started", nullable=False)
    completion_pct = Column(Float, default=0.0, nullable=False)
    time_spent_seconds = Column(Integer, default=0, nullable=False)
    last_position_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("student_id", "path_lesson_id", name="uq_resource_progress_student_lesson"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "not_started")
        kwargs.setdefault("completion_pct", 0.0)
        kwargs.setdefault("time_spent_seconds", 0)
        super().__init__(**kwargs)


class ContentRequest(Base):
    __tablename__ = "content_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subject = Column(String(100), nullable=False)
    grade = Column(Integer, nullable=False)
    topic = Column(String(200), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(50), default="submitted", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "submitted")
        super().__init__(**kwargs)


class LibraryPublicationEvent(Base):
    __tablename__ = "library_publication_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    publisher_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    version_tag = Column(String(50), nullable=False)
    manifest_hash = Column(String(100), nullable=False)
    changes_summary = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
