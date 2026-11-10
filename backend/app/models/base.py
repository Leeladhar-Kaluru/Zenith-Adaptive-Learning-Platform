import uuid
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def uuid_pk():
    from sqlalchemy import Column
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def now_col(**kw):
    from sqlalchemy import Column
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False, **kw)
