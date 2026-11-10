"""Add the recurring_tags and recurring_payment_tags tables.

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-11-10

Free tags the user puts on recurring payments ("Phone", "Savings"), names
encrypted at rest, and the link table between payments and tags.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "d7e8f9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recurring_tags and recurring_payment_tags tables."""
    op.create_table(
        "recurring_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_recurring_tags_user_id", "recurring_tags", ["user_id"])
    op.create_table(
        "recurring_payment_tags",
        sa.Column(
            "payment_id",
            sa.Integer(),
            sa.ForeignKey("recurring_payments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("recurring_tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_recurring_payment_tags_tag_id", "recurring_payment_tags", ["tag_id"]
    )


def downgrade() -> None:
    """Drop the recurring_payment_tags and recurring_tags tables."""
    op.drop_index(
        "ix_recurring_payment_tags_tag_id", table_name="recurring_payment_tags"
    )
    op.drop_table("recurring_payment_tags")
    op.drop_index("ix_recurring_tags_user_id", table_name="recurring_tags")
    op.drop_table("recurring_tags")
