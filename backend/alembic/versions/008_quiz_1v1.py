"""1v1 class quiz: matches, players, answers, quiz ratings

Revision ID: 008
Revises: 007
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "quiz_matches",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("classroom_id", UUID, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="waiting"),
        sa.Column("item_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("deadline_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("winner_id", UUID, sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.CheckConstraint("status in ('waiting','active','done','cancelled')", name="ck_quiz_status"),
    )
    op.create_index("ix_quiz_matches_classroom_id", "quiz_matches", ["classroom_id"])
    op.create_table(
        "quiz_players",
        sa.Column("match_id", UUID, sa.ForeignKey("quiz_matches.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("student_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("theta", sa.Float, nullable=False, server_default="0"),
        sa.Column("score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("finished", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("forfeit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("rating_before", sa.Float),
        sa.Column("rating_after", sa.Float),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_quiz_players_student_id", "quiz_players", ["student_id"])
    op.create_table(
        "quiz_answers",
        sa.Column("match_id", UUID, sa.ForeignKey("quiz_matches.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("student_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True),
        sa.Column("correct", sa.Boolean, nullable=False),
        sa.Column("ms", sa.Integer, nullable=False),
        sa.Column("points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "quiz_ratings",
        sa.Column("student_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("rating", sa.Float, nullable=False, server_default="1000"),
        sa.Column("games", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    for t in ("quiz_ratings", "quiz_answers", "quiz_players", "quiz_matches"):
        op.drop_table(t)
