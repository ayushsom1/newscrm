"""proposals

Revision ID: 0006_proposals
Revises: 0005_complaints
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_proposals"
down_revision: Union[str, None] = "0005_complaints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    source = sa.Enum("AI_DRAFT", "HUMAN", name="proposal_source")
    pstatus = sa.Enum(
        "DRAFT", "APPROVED", "SENT", "REJECTED", name="proposal_status"
    )

    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "advertiser_id",
            sa.Integer(),
            sa.ForeignKey("advertisers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", source, nullable=False),
        sa.Column("status", pstatus, nullable=False, server_default="DRAFT"),
        sa.Column(
            "needs_human",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("needs_human_reason", sa.String(length=200)),
        sa.Column("model_used", sa.String(length=80)),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "approved_by_id",
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
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_proposals_advertiser_id", "proposals", ["advertiser_id"])


def downgrade() -> None:
    op.drop_index("ix_proposals_advertiser_id", table_name="proposals")
    op.drop_table("proposals")
    sa.Enum(name="proposal_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="proposal_source").drop(op.get_bind(), checkfirst=True)
