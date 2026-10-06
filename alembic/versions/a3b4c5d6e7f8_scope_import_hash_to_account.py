"""Scope the import_hash uniqueness to the account.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-10-06

``transactions.import_hash`` was unique across the whole database, so a bank
line already imported into one account could never be imported into another
one.  The uniqueness now applies per ``(account_id, import_hash)``.  Existing
rows are untouched: a globally unique column is also unique per account.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The initial schema created the single-column constraint without a name.
# This convention gives the reflected constraint a name batch mode can drop.
_NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    """Replace the global unique import_hash with a per-account one."""
    with op.batch_alter_table(
        "transactions", recreate="always", naming_convention=_NAMING
    ) as batch_op:
        batch_op.drop_constraint("uq_transactions_import_hash", type_="unique")
        batch_op.create_unique_constraint(
            "uq_transactions_account_import_hash", ["account_id", "import_hash"]
        )


def downgrade() -> None:
    """Restore the global unique constraint on import_hash.

    Fails if two accounts now hold the same import_hash, which is the
    situation this revision exists to allow.
    """
    with op.batch_alter_table(
        "transactions", recreate="always", naming_convention=_NAMING
    ) as batch_op:
        batch_op.drop_constraint("uq_transactions_account_import_hash", type_="unique")
        batch_op.create_unique_constraint(
            "uq_transactions_import_hash", ["import_hash"]
        )
