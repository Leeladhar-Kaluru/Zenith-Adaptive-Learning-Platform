"""class chat: messages, reactions, polls, read marks, reports, blocks, mutes

Revision ID: 006
Revises: 005
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

TABLES = ("chat_messages", "chat_reactions", "chat_poll_votes", "chat_reads", "chat_reports", "chat_blocks", "chat_mutes")
UUID = postgresql.UUID(as_uuid=True)


def _fk(col, target, ondelete="CASCADE", **kw):
    return sa.Column(col, UUID, sa.ForeignKey(target, ondelete=ondelete), **kw)


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "chat_messages", sa.Column("id", UUID, primary_key=True), _fk("classroom_id", "classrooms.id", nullable=False), _fk("author_id", "profiles.id", "SET NULL"),
        sa.Column("kind", sa.String(12), nullable=False, server_default="text"), sa.Column("body", sa.Text, nullable=False, server_default=""),
        _fk("reply_to", "chat_messages.id", "SET NULL"), _fk("parent_id", "chat_messages.id"),
        sa.Column("attachment", postgresql.JSONB), sa.Column("meta", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()), sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("kind in ('text','gif','image','file','poll','announcement')", name="ck_chat_kind"))
    op.create_index("ix_chat_messages_room_time", "chat_messages", ["classroom_id", "created_at"])
    op.create_index("ix_chat_messages_parent", "chat_messages", ["parent_id"])
    op.create_table("chat_reactions", _fk("message_id", "chat_messages.id", primary_key=True), _fk("user_id", "profiles.id", primary_key=True),
                    sa.Column("emoji", sa.String(16), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_table("chat_poll_votes", _fk("message_id", "chat_messages.id", primary_key=True), _fk("user_id", "profiles.id", primary_key=True),
                    sa.Column("option", sa.Integer, nullable=False))
    op.create_table("chat_reads", _fk("classroom_id", "classrooms.id", primary_key=True), _fk("user_id", "profiles.id", primary_key=True),
                    sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("chat_reports", sa.Column("id", UUID, primary_key=True), _fk("classroom_id", "classrooms.id", nullable=False), _fk("message_id", "chat_messages.id", nullable=False),
                    _fk("reporter_id", "profiles.id", nullable=False), sa.Column("reason", sa.String(300), nullable=False),
                    sa.Column("status", sa.String(8), nullable=False, server_default="open"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
                    sa.UniqueConstraint("message_id", "reporter_id", name="uq_chat_report"), sa.CheckConstraint("status in ('open','closed')", name="ck_chat_report_status"))
    op.create_index("ix_chat_reports_classroom_id", "chat_reports", ["classroom_id"])
    op.create_table("chat_blocks", sa.Column("id", UUID, primary_key=True), _fk("blocker_id", "profiles.id", nullable=False), _fk("blocked_id", "profiles.id", nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now), sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_chat_block"))
    op.create_index("ix_chat_blocks_blocker_id", "chat_blocks", ["blocker_id"])
    op.create_table("chat_mutes", _fk("classroom_id", "classrooms.id", primary_key=True), _fk("user_id", "profiles.id", primary_key=True),
                    sa.Column("until", sa.DateTime(timezone=True)), sa.Column("set_by", UUID), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    # Every chat table is reached only through the API, which checks class membership on each call. Browsers get no direct table access.
    names = ",".join(f"'{t}'" for t in TABLES)
    op.execute(f"""
        DO $$ DECLARE t text; BEGIN
          FOREACH t IN ARRAY ARRAY[{names}] LOOP
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', current_schema(), t);
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM anon', current_schema(), t); END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM authenticated', current_schema(), t); END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
