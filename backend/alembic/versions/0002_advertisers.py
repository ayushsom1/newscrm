"""advertisers + contracts

Revision ID: 0002_advertisers
Revises: 0001_users
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_advertisers"
down_revision: Union[str, None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    advertiser_status = sa.Enum(
        "ACTIVE", "INACTIVE", "PROSPECT", name="advertiser_status"
    )
    contract_status = sa.Enum(
        "ACTIVE", "EXPIRED", "CANCELLED", name="contract_status"
    )

    op.create_table(
        "advertisers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=80)),
        sa.Column("contact_name", sa.String(length=120)),
        sa.Column("contact_phone", sa.String(length=40)),
        sa.Column("contact_email", sa.String(length=255)),
        sa.Column("annual_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("spend_trend", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("proposal_open_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("status", advertiser_status, nullable=False, server_default="ACTIVE"),
        sa.Column("churn_score", sa.Integer()),
        sa.Column("churn_band", sa.String(length=8)),
        sa.Column("churn_updated_at", sa.DateTime(timezone=True)),
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
    op.create_index("ix_advertisers_name", "advertisers", ["name"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "advertiser_id",
            sa.Integer(),
            sa.ForeignKey("advertisers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("slots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", contract_status, nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_contracts_advertiser_id", "contracts", ["advertiser_id"])


def downgrade() -> None:
    op.drop_index("ix_contracts_advertiser_id", table_name="contracts")
    op.drop_table("contracts")
    op.drop_index("ix_advertisers_name", table_name="advertisers")
    op.drop_table("advertisers")
    sa.Enum(name="contract_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="advertiser_status").drop(op.get_bind(), checkfirst=True)
