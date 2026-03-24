"""add encryption fields to user

Revision ID: c4d88aefeb0b
Revises: c3d4e5f6a7b8
Create Date: 2026-03-24 14:57:02.393093

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d88aefeb0b"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_encrypted", sa.Boolean(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("encryption_salt", sa.LargeBinary(length=16), nullable=True)
        )
        batch_op.add_column(
            sa.Column("challenge_blob", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("argon2_params", sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("argon2_params")
        batch_op.drop_column("challenge_blob")
        batch_op.drop_column("encryption_salt")
        batch_op.drop_column("is_encrypted")
