"""subscribers + subscriptions + area returns

Revision ID: 0004_subscribers
Revises: 0003_classifieds
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_subscribers"
down_revision: Union[str, None] = "0003_classifieds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    subscriber_plan = sa.Enum(
        "DAILY", "WEEKEND", "SUNDAY_ONLY", name="subscriber_plan"
    )
    subscriber_status = sa.Enum(
        "ACTIVE", "PAUSED", "CANCELLED", name="subscriber_status"
    )
    subscription_status = sa.Enum(
        "ACTIVE", "EXPIRED", "CANCELLED", name="subscription_status"
    )

    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=False),
        sa.Column("address", sa.String(length=255)),
        sa.Column("plan", subscriber_plan, nullable=False, server_default="DAILY"),
        sa.Column("status", subscriber_status, nullable=False, server_default="ACTIVE"),
        sa.Column("missed_payments", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("ix_subscribers_phone", "subscribers", ["phone"], unique=True)
    op.create_index("ix_subscribers_area", "subscribers", ["area"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subscriber_id",
            sa.Integer(),
            sa.ForeignKey("subscribers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", subscriber_plan, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("renew_date", sa.Date(), nullable=False),
        sa.Column(
            "status", subscription_status, nullable=False, server_default="ACTIVE"
        ),
        sa.Column("monthly_price", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_subscriptions_subscriber_id", "subscriptions", ["subscriber_id"]
    )

    op.create_table(
        "area_returns",
        sa.Column("area", sa.String(length=80), primary_key=True),
        sa.Column("returns_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("area_returns")
    op.drop_index("ix_subscriptions_subscriber_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_subscribers_area", table_name="subscribers")
    op.drop_index("ix_subscribers_phone", table_name="subscribers")
    op.drop_table("subscribers")
    sa.Enum(name="subscription_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscriber_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscriber_plan").drop(op.get_bind(), checkfirst=True)
