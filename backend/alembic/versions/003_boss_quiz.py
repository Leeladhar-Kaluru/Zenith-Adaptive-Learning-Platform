"""allow the chapter boss quiz as an assessment kind

Revision ID: 003
Revises: 002
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

OLD = "kind in ('diagnostic','chapter_test','topic_test','revision','practice')"
NEW = "kind in ('diagnostic','chapter_test','topic_test','revision','practice','boss')"


def upgrade() -> None:
    op.drop_constraint("ck_session_kind", "assessment_sessions", type_="check")
    op.create_check_constraint("ck_session_kind", "assessment_sessions", NEW)


def downgrade() -> None:
    op.execute("DELETE FROM assessment_sessions WHERE kind = 'boss'")
    op.drop_constraint("ck_session_kind", "assessment_sessions", type_="check")
    op.create_check_constraint("ck_session_kind", "assessment_sessions", OLD)
