"""Add the recurring_link_refusals table.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-11-08

Link suggestions between two subscription lines the user said no to, so
that they are not made again.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: str | Sequence[str] | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recurring_link_refusals table."""
    op.create_table(
        "recurring_link_refusals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("earlier_key", sa.Text(), nullable=False),
        sa.Column("later_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recurring_link_refusals_user_id", "recurring_link_refusals", ["user_id"]
    )


def downgrade() -> None:
    """Drop the recurring_link_refusals table."""
    op.drop_index(
        "ix_recurring_link_refusals_user_id", table_name="recurring_link_refusals"
    )
    op.drop_table("recurring_link_refusals")
