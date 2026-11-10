import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class StudentReward(Base):
    __tablename__ = "student_rewards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    total_xp = Column(Integer, default=0, nullable=False)
    zenith_coins = Column(Integer, default=0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)
    current_streak_days = Column(Integer, default=0, nullable=False)
    longest_streak_days = Column(Integer, default=0, nullable=False)
    last_active_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("total_xp", 0)
        kwargs.setdefault("zenith_coins", 0)
        kwargs.setdefault("current_level", 1)
        kwargs.setdefault("current_streak_days", 0)
        kwargs.setdefault("longest_streak_days", 0)
        super().__init__(**kwargs)


class RewardEvent(Base):
    __tablename__ = "reward_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    xp_awarded = Column(Integer, default=0, nullable=False)
    coins_awarded = Column(Integer, default=0, nullable=False)
    idempotency_key = Column(String(150), unique=True, nullable=False, index=True)
    meta_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("xp_awarded", 0)
        kwargs.setdefault("coins_awarded", 0)
        super().__init__(**kwargs)


class Badge(Base):
    __tablename__ = "badges"

    id = Column(String(100), primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    icon_url = Column(String(300), nullable=True)
    category = Column(String(50), nullable=False)
    criteria_json = Column(JSON, nullable=False)
    xp_bonus = Column(Integer, default=50, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("xp_bonus", 50)
        super().__init__(**kwargs)


class StudentBadge(Base):
    __tablename__ = "student_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    badge_id = Column(String(100), ForeignKey("badges.id", ondelete="CASCADE"), nullable=False, index=True)
    awarded_at = Column(DateTime, default=datetime.datetime.utcnow)
    idempotency_key = Column(String(150), unique=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badge_student_badge"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
