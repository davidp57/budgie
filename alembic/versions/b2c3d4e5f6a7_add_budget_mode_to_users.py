"""add_budget_mode_and_income_for_month

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add budget_mode to users, income_for_month to transactions."""
    op.add_column(
        "users",
        sa.Column(
            "budget_mode",
            sa.String(length=10),
            nullable=False,
            server_default="n1",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("income_for_month", sa.String(length=7), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema: remove budget_mode and income_for_month."""
    op.drop_column("transactions", "income_for_month")
    op.drop_column("users", "budget_mode")
