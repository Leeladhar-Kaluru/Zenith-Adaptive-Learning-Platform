from sqlalchemy import (Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, text)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk

CONTENT_STATUS = ("draft", "in_review", "changes_requested", "approved", "published", "archived")
CHAPTER_STATUS = ("listed", "in_production", "published", "archived")
ITEM_KINDS = ("mcq", "multi", "truefalse", "numeric", "fill", "match")
_cs = ",".join(f"'{s}'" for s in CONTENT_STATUS)


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String(30), primary_key=True)
    name = Column(String(80), nullable=False)


class CurriculumVersion(Base):
    __tablename__ = "curriculum_versions"
    id = uuid_pk()
    board_id = Column(String(30), ForeignKey("boards.id"), nullable=False)
    label = Column(String(120), nullable=False)
    effective_year = Column(Integer, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)  # chapter mapping checked against the board's textbook
    note = Column(Text)
    __table_args__ = (UniqueConstraint("board_id", "label", name="uq_curriculum_label"),)


class Chapter(Base):
    __tablename__ = "chapters"
    id = uuid_pk()
    version_id = Column(UUID(as_uuid=True), ForeignKey("curriculum_versions.id"), nullable=False, index=True)
    grade = Column(Integer, nullable=False)
    subject_id = Column(String(30), ForeignKey("subjects.id"), nullable=False)
    number = Column(Integer)
    slug = Column(String(120), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="listed")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = now_col()
    __table_args__ = (
        CheckConstraint("grade between 6 and 10", name="ck_chapter_grade"),
        CheckConstraint("status in ('listed','in_production','published','archived')", name="ck_chapter_status"),
        Index("ix_chapters_grade_subject", "grade", "subject_id"),
    )


class Concept(Base):
    __tablename__ = "concepts"
    id = Column(String(120), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    grade = Column(Integer, nullable=False)
    subject_id = Column(String(30), ForeignKey("subjects.id"), nullable=False)
    keywords = Column(JSONB, nullable=False, default=list)
    enrichment = Column(Boolean, nullable=False, default=False)  # extension topic unlocked by mastery
    __table_args__ = (CheckConstraint("grade between 6 and 10", name="ck_concept_grade"),)


class ConceptEdge(Base):
    """prereq_id must be understood before concept_id. The graph must stay acyclic (checked on import)."""
    __tablename__ = "concept_edges"
    prereq_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    strength = Column(Float, nullable=False, default=1.0)
    rationale = Column(Text, nullable=False, default="")
    __table_args__ = (CheckConstraint("prereq_id <> concept_id", name="ck_edge_no_self"),
                      CheckConstraint("strength > 0 and strength <= 1", name="ck_edge_strength"))


class ChapterConcept(Base):
    __tablename__ = "chapter_concepts"
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(12), nullable=False, default="core")


class Lesson(Base):
    __tablename__ = "lessons"
    id = uuid_pk()
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(120), nullable=False)
    position = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("chapter_id", "slug", name="uq_lesson_slug"),
                      UniqueConstraint("chapter_id", "position", name="uq_lesson_position"))


class LessonVersion(Base):
    __tablename__ = "lesson_versions"
    id = uuid_pk()
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    language = Column(String(5), nullable=False, default="en")
    title = Column(String(200), nullable=False)
    minutes = Column(Integer, nullable=False, default=10)
    objectives = Column(JSONB, nullable=False, default=list)
    blocks = Column(JSONB, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="draft")
    origin = Column(String(12), nullable=False, default="human")
    content_hash = Column(String(64), nullable=False)
    author_id = Column(UUID(as_uuid=True))
    reviewer_id = Column(UUID(as_uuid=True))
    reviewed_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    review_note = Column(Text)
    ai_flags = Column(JSONB, nullable=False, default=list)   # AI reviewer notes: flags only, never approval
    created_at = now_col()
    __table_args__ = (
        UniqueConstraint("lesson_id", "version", "language", name="uq_lesson_version"),
        CheckConstraint(f"status in ({_cs})", name="ck_lv_status"),
        CheckConstraint("origin in ('human','ai_assisted')", name="ck_lv_origin"),
        # Nothing reaches students without a named reviewer.
        CheckConstraint("status not in ('approved','published') or (reviewer_id is not null and reviewed_at is not null)", name="ck_lv_reviewed"),
        Index("uq_lv_one_published", "lesson_id", "language", unique=True, postgresql_where=text("status = 'published'")),
    )


class LessonConcept(Base):
    __tablename__ = "lesson_concepts"
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)


class Item(Base):
    """A question. `answer_spec` is server-only and never serialised to students before they answer."""
    __tablename__ = "items"
    id = uuid_pk()
    key = Column(String(160), nullable=False, unique=True)
    kind = Column(String(12), nullable=False)
    stem = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)       # options / pairs / unit / placeholder (public)
    answer_spec = Column(JSONB, nullable=False)                 # correct answer + tolerance (private)
    explanation = Column(Text, nullable=False, default="")
    hints = Column(JSONB, nullable=False, default=list)
    difficulty = Column(String(10), nullable=False, default="standard")
    beta = Column(Float, nullable=False, default=0.0)           # Rasch difficulty, updated online
    n_obs = Column(Integer, nullable=False, default=0)
    purpose = Column(String(10), nullable=False, default="practice")
    status = Column(String(20), nullable=False, default="draft")
    origin = Column(String(12), nullable=False, default="human")
    reviewer_id = Column(UUID(as_uuid=True))
    reviewed_at = Column(DateTime(timezone=True))
    content_hash = Column(String(64), nullable=False)
    created_at = now_col()
    __table_args__ = (
        CheckConstraint("kind in ('mcq','multi','truefalse','numeric','fill','match')", name="ck_item_kind"),
        CheckConstraint("difficulty in ('intro','standard','challenge')", name="ck_item_difficulty"),
        CheckConstraint("purpose in ('check','practice','test','probe')", name="ck_item_purpose"),
        CheckConstraint(f"status in ({_cs})", name="ck_item_status"),
        CheckConstraint("status not in ('approved','published') or (reviewer_id is not null and reviewed_at is not null)", name="ck_item_reviewed"),
    )


class ItemConcept(Base):
    __tablename__ = "item_concepts"
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True, index=True)
    weight = Column(Float, nullable=False, default=1.0)


class Misconception(Base):
    __tablename__ = "misconceptions"
    id = uuid_pk()
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("concept_id", "code", name="uq_misconception"),)


class OptionMisconception(Base):
    __tablename__ = "option_misconceptions"
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    option_key = Column(String(8), primary_key=True)
    misconception_id = Column(UUID(as_uuid=True), ForeignKey("misconceptions.id", ondelete="CASCADE"), nullable=False)


class LessonItem(Base):
    __tablename__ = "lesson_items"
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)


class Card(Base):
    """Flashcard for spaced revision. Reviewed like other content."""
    __tablename__ = "cards"
    id = uuid_pk()
    key = Column(String(160), nullable=False, unique=True)
    concept_id = Column(String(120), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    reviewer_id = Column(UUID(as_uuid=True))
    reviewed_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint(f"status in ({_cs})", name="ck_card_status"),)


class GateResult(Base):
    __tablename__ = "gate_results"
    lesson_version_id = Column(UUID(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String(80), primary_key=True)
    passed = Column(Boolean, nullable=False)
    manual = Column(Boolean, nullable=False, default=False)
    detail = Column(Text, nullable=False, default="")
    acknowledged_by = Column(UUID(as_uuid=True))
    at = now_col()
