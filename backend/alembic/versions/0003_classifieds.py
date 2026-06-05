"""classifieds

Revision ID: 0003_classifieds
Revises: 0002_advertisers
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_classifieds"
down_revision: Union[str, None] = "0002_advertisers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    classified_status = sa.Enum(
        "QUOTED", "PAID", "PUBLISHED", "CANCELLED", name="classified_status"
    )

    op.create_table(
        "classifieds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_phone", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=4), nullable=False, server_default="IN"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
        sa.Column("price_net", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", classified_status, nullable=False, server_default="QUOTED"),
        sa.Column("publish_date", sa.Date()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_classifieds_customer_phone", "classifieds", ["customer_phone"]
    )


def downgrade() -> None:
    op.drop_index("ix_classifieds_customer_phone", table_name="classifieds")
    op.drop_table("classifieds")
    sa.Enum(name="classified_status").drop(op.get_bind(), checkfirst=True)
