"""Where every imported asset came from, under which licence, and who must be credited. Nothing is shown to students without this."""
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, now_col, uuid_pk

ASSET_STATUS = ("pending", "approved", "rejected", "retired")


class Source(Base):
    __tablename__ = "sources"
    id = uuid_pk()
    name = Column(String(120), nullable=False, unique=True)
    homepage = Column(String(300), nullable=False)
    licence_terms_url = Column(String(300), nullable=False, default="")
    api_terms_url = Column(String(300), nullable=False, default="")
    robots_ok = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=False, default="")
    created_at = now_col()


class SourceAsset(Base):
    __tablename__ = "source_assets"
    id = uuid_pk()
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True)
    external_id = Column(String(300), nullable=False)
    url = Column(String(600), nullable=False)
    kind = Column(String(16), nullable=False)                 # image, dataset, simulation, geo
    licence_id = Column(String(40), nullable=False)
    attribution_text = Column(Text, nullable=False, default="")
    author = Column(String(300), nullable=False, default="")
    sha256 = Column(String(64), nullable=False, default="")
    bytes = Column(BigInteger, nullable=False, default=0)
    storage_path = Column(String(300))
    status = Column(String(10), nullable=False, default="pending")
    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    recheck_at = Column(DateTime(timezone=True), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True))
    created_at = now_col()
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_asset_source_external"),
        CheckConstraint("length(licence_id) > 0", name="ck_asset_licence"),
        CheckConstraint("status in ('pending','approved','rejected','retired')", name="ck_asset_status"),
        CheckConstraint("status <> 'approved' or length(attribution_text) > 0", name="ck_asset_attribution"),
        Index("ix_asset_recheck", "recheck_at"),
    )


class ContentProvenance(Base):
    __tablename__ = "content_provenance"
    lesson_version_id = Column(UUID(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="CASCADE"), primary_key=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("source_assets.id", ondelete="RESTRICT"), primary_key=True)
