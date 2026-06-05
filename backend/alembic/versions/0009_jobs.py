"""job runs

Revision ID: 0009_jobs
Revises: 0008_tenders
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_jobs"
down_revision: Union[str, None] = "0008_tenders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_status = sa.Enum("SUCCESS", "FAILED", "SKIPPED", name="job_status")
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=60), nullable=False),
        sa.Column("window_date", sa.Date(), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notifications_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column(
            "triggered_by",
            sa.String(length=40),
            nullable=False,
            server_default="SCHEDULER",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "job_name", "window_date", name="uq_job_runs_job_window"
        ),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])


def downgrade() -> None:
    op.drop_index("ix_job_runs_job_name", table_name="job_runs")
    op.drop_table("job_runs")
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=True)
