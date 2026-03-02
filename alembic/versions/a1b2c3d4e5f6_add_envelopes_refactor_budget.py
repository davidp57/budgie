"""add_envelopes_refactor_budget_allocations

Revision ID: a1b2c3d4e5f6
Revises: df8311bab1a1
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "df8311bab1a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add envelopes + envelope_categories, refactor budget_allocations."""
    # 1. Create envelopes table
    op.create_table(
        "envelopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rollover", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create envelope_categories association table
    op.create_table(
        "envelope_categories",
        sa.Column("envelope_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["envelope_id"],
            ["envelopes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("envelope_id", "category_id"),
    )

    # 3. Refactor budget_allocations: replace category_id with envelope_id.
    #    Use batch_alter_table for SQLite compatibility (requires full table rebuild).
    #    Existing allocations are deleted because there are no envelopes yet.
    with op.batch_alter_table(
        "budget_allocations", recreate="always"
    ) as batch_op:
        batch_op.drop_constraint("uq_category_month", type_="unique")
        batch_op.drop_column("category_id")
        batch_op.add_column(
            sa.Column("envelope_id", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_foreign_key(
            "fk_budget_allocations_envelope_id",
            "envelopes",
            ["envelope_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_envelope_month", ["envelope_id", "month"]
        )


def downgrade() -> None:
    """Downgrade schema: restore category_id, drop envelopes tables."""
    with op.batch_alter_table(
        "budget_allocations", recreate="always"
    ) as batch_op:
        batch_op.drop_constraint("uq_envelope_month", type_="unique")
        batch_op.drop_constraint("fk_budget_allocations_envelope_id", type_="foreignkey")
        batch_op.drop_column("envelope_id")
        batch_op.add_column(
            sa.Column("category_id", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_foreign_key(
            "fk_budget_allocations_category_id",
            "categories",
            ["category_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_category_month", ["category_id", "month"]
        )

    op.drop_table("envelope_categories")
    op.drop_table("envelopes")
