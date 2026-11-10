from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk

ROLES = ("student", "teacher", "reviewer", "admin")


class Board(Base):
    __tablename__ = "boards"
    id = Column(String(30), primary_key=True)
    name = Column(String(120), nullable=False)
    active = Column(Boolean, nullable=False, default=True)


class Profile(Base):
    """One row per auth user. `id` equals the Supabase auth user id."""
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255))
    role = Column(String(20), nullable=False, default="student", index=True)
    display_name = Column(String(120), nullable=False)
    nickname = Column(String(24))
    avatar = Column(String(24))
    grade = Column(Integer)
    board_id = Column(String(30), ForeignKey("boards.id"))
    language = Column(String(5), nullable=False, default="en")
    goals = Column(JSONB, nullable=False, default=list)
    subjects = Column(JSONB, nullable=False, default=list)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    consent_status = Column(String(20), nullable=False, default="pending")
    consent_at = Column(DateTime(timezone=True))
    league_opt_out = Column(Boolean, nullable=False, default=False)
    created_at = now_col()
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        CheckConstraint("role in ('student','teacher','reviewer','admin')", name="ck_profile_role"),
        CheckConstraint("grade is null or grade between 6 and 10", name="ck_profile_grade"),
        CheckConstraint("language in ('en','hi','te')", name="ck_profile_language"),
        CheckConstraint("consent_status in ('not_required','pending','granted','withdrawn')", name="ck_profile_consent"),
    )


class ConsentEvent(Base):
    __tablename__ = "consent_events"
    id = uuid_pk()
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    method = Column(String(40), nullable=False)  # self_declared_adult | guardian_statement | school
    actor_id = Column(UUID(as_uuid=True))
    at = now_col()


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(UUID(as_uuid=True), index=True)
    action = Column(String(60), nullable=False)
    entity = Column(String(60), nullable=False)
    entity_id = Column(String(80))
    detail = Column(JSONB, nullable=False, default=dict)
    at = now_col()
