"""Add fields_encrypted column to users table.

Tracks whether the user's field-level data (transaction memos, payee names)
has actually been encrypted.  Distinct from ``is_encrypted``, which only
indicates that encryption has been *configured* for the account.  This flag
is set to True by ``encrypt_user_data`` once the migration is complete.

Having a dedicated flag allows the ``/unlock`` endpoint to detect the case
where ``is_encrypted=True`` was written by an older server version that
never actually ran the field-level encryption migration, and to trigger the
migration transparently at next unlock.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add fields_encrypted column (default False) to users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "fields_encrypted",
                sa.Boolean(),
                server_default="0",
                nullable=False,
            )
        )


def downgrade() -> None:
    """Remove fields_encrypted column from users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("fields_encrypted")
