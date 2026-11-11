from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk


class QuizMatch(Base):
    """A 1v1 quiz inside one class. The questions are fixed when the second player joins, so both play the same ones."""
    __tablename__ = "quiz_matches"
    id = uuid_pk()
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(10), nullable=False, default="waiting")
    item_ids = Column(JSONB, nullable=False, default=list)
    created_at = now_col()
    started_at = Column(DateTime(timezone=True))
    deadline_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    winner_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    detail = Column(JSONB, nullable=False, default=dict)          # how the questions were picked (seed, target difficulty): the audit trail
    __table_args__ = (CheckConstraint("status in ('waiting','active','done','cancelled')", name="ck_quiz_status"),)


class QuizPlayer(Base):
    __tablename__ = "quiz_players"
    match_id = Column(UUID(as_uuid=True), ForeignKey("quiz_matches.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True, index=True)
    theta = Column(Float, nullable=False, default=0.0)            # learner rating when matched, used for pairing
    score = Column(Integer, nullable=False, default=0)
    finished = Column(Boolean, nullable=False, default=False)
    forfeit = Column(Boolean, nullable=False, default=False)
    rating_before = Column(Float)
    rating_after = Column(Float)
    joined_at = now_col()


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    match_id = Column(UUID(as_uuid=True), ForeignKey("quiz_matches.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer, primary_key=True)
    correct = Column(Boolean, nullable=False)
    ms = Column(Integer, nullable=False)                          # measured by the server, never sent by the browser
    points = Column(Integer, nullable=False, default=0)
    created_at = now_col()


class QuizRating(Base):
    """Elo for 1v1 quizzes only. It is separate from the learner model, so a quiz can never change what ZENITH thinks a student has mastered."""
    __tablename__ = "quiz_ratings"
    student_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    rating = Column(Float, nullable=False, default=1000.0)
    games = Column(Integer, nullable=False, default=0)
