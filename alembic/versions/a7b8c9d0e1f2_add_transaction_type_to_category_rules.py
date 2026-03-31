"""Add transaction_type to category_rules.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-27

Adds a ``transaction_type`` column to ``category_rules``.  The column is a
non-nullable VARCHAR with a server default of ``'any'``, so existing rules
behave as before (match any transaction regardless of sign).

Possible values:
- ``any``    — matches both debits and credits (default)
- ``debit``  — matches only negative-amount transactions (bank debits /
               expenses)
- ``credit`` — matches only positive-amount transactions (income, refunds,
               avoirs)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add transaction_type column with default 'any' to category_rules."""
    op.add_column(
        "category_rules",
        sa.Column(
            "transaction_type",
            sa.String(10),
            nullable=False,
            server_default="any",
        ),
    )


def downgrade() -> None:
    """Remove transaction_type column from category_rules."""
    op.drop_column("category_rules", "transaction_type")
