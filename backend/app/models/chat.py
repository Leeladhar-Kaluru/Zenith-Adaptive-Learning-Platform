from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, now_col, uuid_pk

KINDS = ("text", "gif", "image", "file", "poll", "announcement")


class ChatMessage(Base):
    """One message in a class chat. There are no private messages: every row belongs to exactly one classroom."""
    __tablename__ = "chat_messages"
    id = uuid_pk()
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    kind = Column(String(12), nullable=False, default="text")
    body = Column(Text, nullable=False, default="")
    reply_to = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"))
    parent_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"))   # thread root; null for top-level
    attachment = Column(JSONB)      # {key, name, type, size} for image/file; {url, title, provider} for gif
    meta = Column(JSONB, nullable=False, default=dict)   # poll options
    pinned = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True))
    created_at = now_col()
    __table_args__ = (CheckConstraint("kind in ('text','gif','image','file','poll','announcement')", name="ck_chat_kind"),)


class ChatReaction(Base):
    __tablename__ = "chat_reactions"
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    emoji = Column(String(16), primary_key=True)
    created_at = now_col()


class ChatPollVote(Base):
    __tablename__ = "chat_poll_votes"
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    option = Column(Integer, nullable=False)


class ChatRead(Base):
    __tablename__ = "chat_reads"
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    last_read_at = Column(DateTime(timezone=True), nullable=False)


class ChatReport(Base):
    __tablename__ = "chat_reports"
    id = uuid_pk()
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(300), nullable=False)
    status = Column(String(8), nullable=False, default="open")
    created_at = now_col()
    __table_args__ = (UniqueConstraint("message_id", "reporter_id", name="uq_chat_report"), CheckConstraint("status in ('open','closed')", name="ck_chat_report_status"))


class ChatBlock(Base):
    __tablename__ = "chat_blocks"
    id = uuid_pk()
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    created_at = now_col()
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_chat_block"),)


class ChatMute(Base):
    """A teacher has silenced a student in one class (until a time, or until lifted)."""
    __tablename__ = "chat_mutes"
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    until = Column(DateTime(timezone=True))
    set_by = Column(UUID(as_uuid=True))
    created_at = now_col()
