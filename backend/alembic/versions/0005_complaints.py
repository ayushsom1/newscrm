"""complaints + audit log

Revision ID: 0005_complaints
Revises: 0004_subscribers
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_complaints"
down_revision: Union[str, None] = "0004_subscribers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    triage = sa.Enum("PENDING", "AUTO", "ESCALATED", name="complaint_triage")
    cstatus = sa.Enum("OPEN", "RESOLVED", "CANCELLED", name="complaint_status")
    channel = sa.Enum(
        "PHONE", "EMAIL", "WHATSAPP", "WALK_IN", name="complaint_channel"
    )

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscriber_name", sa.String(length=160), nullable=False),
        sa.Column("subscriber_phone", sa.String(length=40)),
        sa.Column("area", sa.String(length=80)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("channel", channel, nullable=False, server_default="PHONE"),
        sa.Column("triage", triage, nullable=False, server_default="PENDING"),
        sa.Column("triage_reason", sa.Text()),
        sa.Column("triage_source", sa.String(length=20)),
        sa.Column("resolution", sa.Text()),
        sa.Column("status", cstatus, nullable=False, server_default="OPEN"),
        sa.Column(
            "assigned_to_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_complaints_subscriber_phone", "complaints", ["subscriber_phone"]
    )
    op.create_index("ix_complaints_assigned_to_id", "complaints", ["assigned_to_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("payload", sa.JSON()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_complaints_assigned_to_id", table_name="complaints")
    op.drop_index("ix_complaints_subscriber_phone", table_name="complaints")
    op.drop_table("complaints")
    sa.Enum(name="complaint_channel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="complaint_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="complaint_triage").drop(op.get_bind(), checkfirst=True)
