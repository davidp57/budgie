"""Add the recurring_payment_aliases table.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-11-08

Bank labels merged into a classified recurring payment, after the bank or
the merchant renamed a debit.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6d7e8f9a0b1"
down_revision: str | Sequence[str] | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recurring_payment_aliases table."""
    op.create_table(
        "recurring_payment_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Integer(),
            sa.ForeignKey("recurring_payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_key", sa.Text(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recurring_payment_aliases_payment_id",
        "recurring_payment_aliases",
        ["payment_id"],
    )


def downgrade() -> None:
    """Drop the recurring_payment_aliases table."""
    op.drop_index(
        "ix_recurring_payment_aliases_payment_id",
        table_name="recurring_payment_aliases",
    )
    op.drop_table("recurring_payment_aliases")
