"""add_reconciled_with_id_to_transactions

Adds a nullable self-referential FK on transactions so that a budget
transaction (planned/real) can be linked to a bank-imported transaction
for the reconciliation (pointage) feature.

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-03-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "69e73afdd24c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add reconciled_with_id to transactions."""
    with op.batch_alter_table("transactions", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column("reconciled_with_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_transactions_reconciled_with_id",
            "transactions",
            ["reconciled_with_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema: remove reconciled_with_id from transactions."""
    with op.batch_alter_table("transactions", recreate="auto") as batch_op:
        batch_op.drop_constraint(
            "fk_transactions_reconciled_with_id", type_="foreignkey"
        )
        batch_op.drop_column("reconciled_with_id")
