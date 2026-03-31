"""Add min_amount and max_amount to category_rules.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-26

Adds optional amount range constraints (min_amount, max_amount) to
CategoryRule.  Both columns are nullable integers (centimes).  When set,
the categorization engine only applies the rule when the transaction
amount falls within [min_amount, max_amount].
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable min_amount and max_amount columns to category_rules table."""
    op.add_column(
        "category_rules",
        sa.Column("min_amount", sa.Integer(), nullable=True),
    )
    op.add_column(
        "category_rules",
        sa.Column("max_amount", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove min_amount and max_amount columns from category_rules table."""
    op.drop_column("category_rules", "max_amount")
    op.drop_column("category_rules", "min_amount")
