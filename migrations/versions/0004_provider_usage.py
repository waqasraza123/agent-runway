"""provider usage ledger

Revision ID: 0004_provider_usage
Revises: 0003_event_observability
Create Date: 2026-05-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_provider_usage"
down_revision: str | None = "0003_event_observability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    if not _table_exists("provider_usage_records"):
        op.create_table(
            "provider_usage_records",
            sa.Column("usage_id", sa.String(length=64), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=False),
            sa.Column("operation", sa.String(length=32), nullable=False),
            sa.Column("provider_name", sa.String(length=64), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
            sa.ForeignKeyConstraint(["run_id"], ["run_states.run_id"]),
            sa.PrimaryKeyConstraint("usage_id"),
        )

    _create_index_if_missing(
        "ix_provider_usage_tenant_created_at",
        "provider_usage_records",
        ["tenant_id", "created_at"],
    )
    _create_index_if_missing(
        "ix_provider_usage_run_id",
        "provider_usage_records",
        ["run_id"],
    )
    _create_index_if_missing(
        "ix_provider_usage_tenant_run_id",
        "provider_usage_records",
        ["tenant_id", "run_id"],
    )
    _create_index_if_missing(
        "ix_provider_usage_operation",
        "provider_usage_records",
        ["operation"],
    )
    _create_index_if_missing(
        "ix_provider_usage_provider_model",
        "provider_usage_records",
        ["provider_name", "model_name"],
    )


def downgrade() -> None:
    _drop_index_if_exists("ix_provider_usage_provider_model", "provider_usage_records")
    _drop_index_if_exists("ix_provider_usage_operation", "provider_usage_records")
    _drop_index_if_exists("ix_provider_usage_tenant_run_id", "provider_usage_records")
    _drop_index_if_exists("ix_provider_usage_run_id", "provider_usage_records")
    _drop_index_if_exists("ix_provider_usage_tenant_created_at", "provider_usage_records")
    if _table_exists("provider_usage_records"):
        op.drop_table("provider_usage_records")
