"""optional self-reported confidence on an answer (1 guessing, 2 not sure, 3 sure), for calibration

Revision ID: 011
Revises: 010
"""
import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence_events", sa.Column("confidence", sa.SmallInteger))
    op.create_check_constraint("ck_evidence_confidence", "evidence_events", "confidence is null or confidence between 1 and 3")


def downgrade() -> None:
    op.drop_constraint("ck_evidence_confidence", "evidence_events", type_="check")
    op.drop_column("evidence_events", "confidence")
