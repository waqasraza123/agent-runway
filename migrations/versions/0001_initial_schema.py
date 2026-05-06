"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    index_names = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }
    return index_name in index_names


def _create_table_if_missing(table_name: str, *columns: object) -> None:
    if not _table_exists(table_name):
        op.create_table(table_name, *columns)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_table_if_exists(table_name: str) -> None:
    if _table_exists(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    _create_table_if_missing(
        "run_states",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    _create_index_if_missing("ix_run_states_created_at", "run_states", ["created_at"])
    _create_index_if_missing("ix_run_states_status", "run_states", ["status"])
    _create_index_if_missing("ix_run_states_updated_at", "run_states", ["updated_at"])
    _create_index_if_missing("ix_run_states_workflow_type", "run_states", ["workflow_type"])

    _create_table_if_missing(
        "run_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    _create_index_if_missing("ix_run_events_event_type", "run_events", ["event_type"])
    _create_index_if_missing("ix_run_events_occurred_at", "run_events", ["occurred_at"])
    _create_index_if_missing("ix_run_events_run_id", "run_events", ["run_id"])

    _create_table_if_missing(
        "run_approvals",
        sa.Column("approval_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("approval_id"),
    )
    _create_index_if_missing("ix_run_approvals_requested_at", "run_approvals", ["requested_at"])
    _create_index_if_missing("ix_run_approvals_run_id", "run_approvals", ["run_id"])
    _create_index_if_missing("ix_run_approvals_status", "run_approvals", ["status"])

    _create_table_if_missing(
        "run_verifications",
        sa.Column("verification_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("verification_id"),
    )
    _create_index_if_missing(
        "ix_run_verifications_created_at", "run_verifications", ["created_at"]
    )
    _create_index_if_missing("ix_run_verifications_run_id", "run_verifications", ["run_id"])
    _create_index_if_missing("ix_run_verifications_verdict", "run_verifications", ["verdict"])

    _create_table_if_missing(
        "run_plans",
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("plan_id"),
    )
    _create_index_if_missing("ix_run_plans_created_at", "run_plans", ["created_at"])
    _create_index_if_missing("ix_run_plans_run_id", "run_plans", ["run_id"])

    _create_table_if_missing(
        "run_turns",
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("turn_id"),
    )
    _create_index_if_missing("ix_run_turns_created_at", "run_turns", ["created_at"])
    _create_index_if_missing("ix_run_turns_run_id", "run_turns", ["run_id"])
    _create_index_if_missing("ix_run_turns_task_id", "run_turns", ["task_id"])

    _create_table_if_missing(
        "run_tool_calls",
        sa.Column("tool_call_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tool_call_id"),
    )
    _create_index_if_missing("ix_run_tool_calls_created_at", "run_tool_calls", ["created_at"])
    _create_index_if_missing("ix_run_tool_calls_run_id", "run_tool_calls", ["run_id"])
    _create_index_if_missing("ix_run_tool_calls_task_id", "run_tool_calls", ["task_id"])
    _create_index_if_missing("ix_run_tool_calls_turn_id", "run_tool_calls", ["turn_id"])

    _create_table_if_missing(
        "run_llm_calls",
        sa.Column("llm_call_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("llm_call_id"),
    )
    _create_index_if_missing("ix_run_llm_calls_created_at", "run_llm_calls", ["created_at"])
    _create_index_if_missing(
        "ix_run_llm_calls_provider_name", "run_llm_calls", ["provider_name"]
    )
    _create_index_if_missing("ix_run_llm_calls_run_id", "run_llm_calls", ["run_id"])
    _create_index_if_missing("ix_run_llm_calls_task_id", "run_llm_calls", ["task_id"])
    _create_index_if_missing("ix_run_llm_calls_turn_id", "run_llm_calls", ["turn_id"])

    _create_table_if_missing(
        "run_outputs",
        sa.Column("output_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("output_id"),
    )
    _create_index_if_missing("ix_run_outputs_created_at", "run_outputs", ["created_at"])
    _create_index_if_missing("ix_run_outputs_run_id", "run_outputs", ["run_id"])


def downgrade() -> None:
    _drop_index_if_exists("ix_run_outputs_run_id", "run_outputs")
    _drop_index_if_exists("ix_run_outputs_created_at", "run_outputs")
    _drop_table_if_exists("run_outputs")

    _drop_index_if_exists("ix_run_llm_calls_turn_id", "run_llm_calls")
    _drop_index_if_exists("ix_run_llm_calls_task_id", "run_llm_calls")
    _drop_index_if_exists("ix_run_llm_calls_run_id", "run_llm_calls")
    _drop_index_if_exists("ix_run_llm_calls_provider_name", "run_llm_calls")
    _drop_index_if_exists("ix_run_llm_calls_created_at", "run_llm_calls")
    _drop_table_if_exists("run_llm_calls")

    _drop_index_if_exists("ix_run_tool_calls_turn_id", "run_tool_calls")
    _drop_index_if_exists("ix_run_tool_calls_task_id", "run_tool_calls")
    _drop_index_if_exists("ix_run_tool_calls_run_id", "run_tool_calls")
    _drop_index_if_exists("ix_run_tool_calls_created_at", "run_tool_calls")
    _drop_table_if_exists("run_tool_calls")

    _drop_index_if_exists("ix_run_turns_task_id", "run_turns")
    _drop_index_if_exists("ix_run_turns_run_id", "run_turns")
    _drop_index_if_exists("ix_run_turns_created_at", "run_turns")
    _drop_table_if_exists("run_turns")

    _drop_index_if_exists("ix_run_plans_run_id", "run_plans")
    _drop_index_if_exists("ix_run_plans_created_at", "run_plans")
    _drop_table_if_exists("run_plans")

    _drop_index_if_exists("ix_run_verifications_verdict", "run_verifications")
    _drop_index_if_exists("ix_run_verifications_run_id", "run_verifications")
    _drop_index_if_exists("ix_run_verifications_created_at", "run_verifications")
    _drop_table_if_exists("run_verifications")

    _drop_index_if_exists("ix_run_approvals_status", "run_approvals")
    _drop_index_if_exists("ix_run_approvals_run_id", "run_approvals")
    _drop_index_if_exists("ix_run_approvals_requested_at", "run_approvals")
    _drop_table_if_exists("run_approvals")

    _drop_index_if_exists("ix_run_events_run_id", "run_events")
    _drop_index_if_exists("ix_run_events_occurred_at", "run_events")
    _drop_index_if_exists("ix_run_events_event_type", "run_events")
    _drop_table_if_exists("run_events")

    _drop_index_if_exists("ix_run_states_workflow_type", "run_states")
    _drop_index_if_exists("ix_run_states_updated_at", "run_states")
    _drop_index_if_exists("ix_run_states_status", "run_states")
    _drop_index_if_exists("ix_run_states_created_at", "run_states")
    _drop_table_if_exists("run_states")
