"""autonomy config singleton

Revision ID: 0010_autonomy
Revises: 0009_jobs
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_autonomy"
down_revision: Union[str, None] = "0009_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "autonomy_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "triage_ai_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "triage_auto_resolve_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "ai_draft_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "high_churn_always_needs_human",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "assistant_actions_require_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "locale", sa.String(length=4), nullable=False, server_default="IN"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_by_id", sa.Integer()),
    )
    # Seed the singleton row so callers can always rely on id=1 being present.
    op.execute("INSERT INTO autonomy_config (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("autonomy_config")
