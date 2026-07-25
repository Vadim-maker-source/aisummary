"""Add evidence-based value metrics.

Revision ID: 20260725_0003
Revises: 20260725_0002
Create Date: 2026-07-25
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_0003"
down_revision: str | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_events",
        sa.Column("task_completed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "agent_events",
        sa.Column("estimated_minutes_saved", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_minutes_saved",
        "agent_events",
        "estimated_minutes_saved IS NULL OR estimated_minutes_saved >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_minutes_saved",
        "agent_events",
        type_="check",
    )
    op.drop_column("agent_events", "estimated_minutes_saved")
    op.drop_column("agent_events", "task_completed")
