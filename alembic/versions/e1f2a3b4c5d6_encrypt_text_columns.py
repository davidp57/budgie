"""encrypt_text_columns

Change memo (transactions) and name (payees) from VARCHAR to TEXT so they can
store AES-256-GCM base64 blobs, which are longer than the original VARCHAR
size limits.

Revision ID: e1f2a3b4c5d6
Revises: b8c9d0e1f2a3
Create Date: 2026-03-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: widen memo and payee name columns to TEXT."""
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column(
            "memo",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )

    with op.batch_alter_table("payees", schema=None) as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=200),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema: restore VARCHAR size limits."""
    with op.batch_alter_table("payees", schema=None) as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.Text(),
            type_=sa.String(length=200),
            existing_nullable=False,
        )

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column(
            "memo",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
