"""Initial analytics schema.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260724_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "total_rows", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "processed_rows", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "failed_rows", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "error_log",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("import_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column(
            "stream", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "raw_request",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "raw_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("agent_answer", sa.Text(), nullable=True),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("analysis_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_latency",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_rating",
        ),
        sa.ForeignKeyConstraint(
            ["import_id"],
            ["imports.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_id",
            "external_id",
            name="uq_event_agent_external",
        ),
    )
    op.create_index(
        "ix_events_analysis_status",
        "agent_events",
        ["analysis_status"],
    )
    op.create_index("ix_events_import_id", "agent_events", ["import_id"])
    op.create_index("ix_events_occurred_at", "agent_events", ["occurred_at"])

    op.create_table(
        "event_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("effective_user_query", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column(
            "classification_confidence",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
        ),
        sa.Column(
            "query_problem_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "automation_potential", sa.String(length=16), nullable=False
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("classifier_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["agent_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_analyses_category", "event_analyses", ["category"]
    )
    op.create_index(
        "ix_analyses_created_at", "event_analyses", ["created_at"]
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger_import_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["trigger_import_id"],
            ["imports.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trigger_import_id"),
    )
    op.create_index(
        "ix_analysis_runs_current", "analysis_runs", ["is_current"]
    )
    op.create_index(
        "ix_analysis_runs_status", "analysis_runs", ["status"]
    )

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "representative_queries",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "common_problems",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "automation_potential", sa.String(length=16), nullable=False
        ),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenarios_run_category",
        "scenarios",
        ["analysis_run_id", "category"],
    )

    op.create_table(
        "scenario_members",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "similarity", sa.Numeric(precision=4, scale=3), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["agent_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scenario_id", "event_id"),
    )
    op.create_index(
        "ix_scenario_members_event",
        "scenario_members",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_members_event", table_name="scenario_members")
    op.drop_table("scenario_members")
    op.drop_index("ix_scenarios_run_category", table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_current", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("ix_analyses_created_at", table_name="event_analyses")
    op.drop_index("ix_analyses_category", table_name="event_analyses")
    op.drop_table("event_analyses")
    op.drop_index("ix_events_occurred_at", table_name="agent_events")
    op.drop_index("ix_events_import_id", table_name="agent_events")
    op.drop_index("ix_events_analysis_status", table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_table("imports")

