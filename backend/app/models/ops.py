from sqlalchemy import CheckConstraint, Column, DateTime, Float, Index, String

from app.models.base import Base, now_col, uuid_pk

VITAL_NAMES = ("LCP", "INP", "CLS", "TTFB", "FCP")


class WebVital(Base):
    """A real-user speed measurement. Deliberately has no user id: it only says how fast a route was."""
    __tablename__ = "web_vitals"
    id = uuid_pk()
    name = Column(String(6), nullable=False)
    value = Column(Float, nullable=False)
    route = Column(String(80), nullable=False)
    at = now_col()
    __table_args__ = (
        CheckConstraint("name in (" + ",".join(f"'{n}'" for n in VITAL_NAMES) + ")", name="ck_vital_name"),
        CheckConstraint("value >= 0 and value <= 600000", name="ck_vital_value"),
        Index("ix_vital_route_name", "route", "name"),
    )
