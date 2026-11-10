from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk


class Classroom(Base):
    __tablename__ = "classrooms"
    id = uuid_pk()
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    grade = Column(Integer, nullable=False)
    subject_id = Column(String(30), ForeignKey("subjects.id"), nullable=False)
    board_id = Column(String(30), ForeignKey("boards.id"), nullable=False)
    join_code = Column(String(12), nullable=False, unique=True)
    leagues_enabled = Column(Boolean, nullable=False, default=True)
    created_at = now_col()
    __table_args__ = (CheckConstraint("grade between 6 and 10", name="ck_class_grade"),)


class ClassMember(Base):
    __tablename__ = "class_members"
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True, index=True)
    joined_at = now_col()
    status = Column(String(10), nullable=False, default="active")


class Assignment(Base):
    __tablename__ = "assignments"
    id = uuid_pk()
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(12), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"))
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    concept_ids = Column(JSONB, nullable=False, default=list)
    title = Column(String(160), nullable=False)
    note = Column(Text)
    due_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(JSONB)   # evidence that motivated the assignment, if any
    created_at = now_col()
    __table_args__ = (CheckConstraint("kind in ('lesson','practice','test','revision')", name="ck_assignment_kind"),)


class TeacherDecision(Base):
    """Teacher accepted or dismissed a ZENITH suggestion. Teachers always have the last word."""
    __tablename__ = "teacher_decisions"
    id = uuid_pk()
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    suggestion_key = Column(String(120), nullable=False)
    action = Column(String(10), nullable=False)
    note = Column(Text)
    at = now_col()
    __table_args__ = (UniqueConstraint("classroom_id", "suggestion_key", name="uq_decision"),
                      CheckConstraint("action in ('accepted','dismissed')", name="ck_decision_action"))


class XpEvent(Base):
    __tablename__ = "xp_events"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)
    amount = Column(Integer, nullable=False)
    idem_key = Column(String(120), nullable=False)
    created_at = now_col()
    __table_args__ = (UniqueConstraint("student_id", "idem_key", name="uq_xp_idem"), CheckConstraint("amount > 0", name="ck_xp_positive"))


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    day = Column(Date, primary_key=True)
    answers = Column(Integer, nullable=False, default=0)
    correct = Column(Integer, nullable=False, default=0)
    lessons = Column(Integer, nullable=False, default=0)
    xp = Column(Integer, nullable=False, default=0)
    rest_day = Column(Boolean, nullable=False, default=False)


class StudentBadge(Base):
    __tablename__ = "student_badges"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    code = Column(String(40), primary_key=True)
    earned_at = now_col()


class LeagueMembership(Base):
    __tablename__ = "league_memberships"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    tier = Column(String(10), nullable=False, default="foothill")
    last_week = Column(Date)


class TutorThread(Base):
    __tablename__ = "tutor_threads"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"))
    created_at = now_col()


class TutorMessage(Base):
    __tablename__ = "tutor_messages"
    id = uuid_pk()
    thread_id = Column(UUID(as_uuid=True), ForeignKey("tutor_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(String(5), nullable=False, default="en")
    meta = Column(JSONB, nullable=False, default=dict)
    created_at = now_col()
    __table_args__ = (CheckConstraint("role in ('student','tutor')", name="ck_tutor_role"),)
