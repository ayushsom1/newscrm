"""gov tenders

Revision ID: 0008_tenders
Revises: 0007_assistant
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_tenders"
down_revision: Union[str, None] = "0007_assistant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tender_status = sa.Enum(
        "OPEN", "SUBMITTED", "WON", "LOST", "CLOSED", name="tender_status"
    )
    op.create_table(
        "gov_tenders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("est_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", tender_status, nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text()),
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
    )
    op.create_index("ix_gov_tenders_deadline", "gov_tenders", ["deadline"])


def downgrade() -> None:
    op.drop_index("ix_gov_tenders_deadline", table_name="gov_tenders")
    op.drop_table("gov_tenders")
    sa.Enum(name="tender_status").drop(op.get_bind(), checkfirst=True)
