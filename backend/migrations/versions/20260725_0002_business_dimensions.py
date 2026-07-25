"""Add business dimensions and synthetic-data marker.

Revision ID: 20260725_0002
Revises: 20260724_0001
Create Date: 2026-07-25
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_0002"
down_revision: str | None = "20260724_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_events",
        sa.Column("user_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent_events",
        sa.Column("team", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent_events",
        sa.Column("direction", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent_events",
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE agent_events SET is_synthetic = true "
        "WHERE agent_id = 'synthetic-demo-agent'"
    )
    op.create_index("ix_events_team", "agent_events", ["team"])
    op.create_index("ix_events_direction", "agent_events", ["direction"])


def downgrade() -> None:
    op.drop_index("ix_events_direction", table_name="agent_events")
    op.drop_index("ix_events_team", table_name="agent_events")
    op.drop_column("agent_events", "is_synthetic")
    op.drop_column("agent_events", "direction")
    op.drop_column("agent_events", "team")
    op.drop_column("agent_events", "user_id")
