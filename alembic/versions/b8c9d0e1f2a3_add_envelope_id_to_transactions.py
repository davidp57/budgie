"""add_envelope_id_to_transactions

Adds a nullable FK on transactions pointing to envelopes so that
manually-created expenses can be linked directly to an envelope,
without requiring a category assignment.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-03-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add envelope_id to transactions."""
    with op.batch_alter_table("transactions", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("envelope_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_transactions_envelope_id",
            "envelopes",
            ["envelope_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema: remove envelope_id from transactions."""
    with op.batch_alter_table("transactions", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_transactions_envelope_id", type_="foreignkey")
        batch_op.drop_column("envelope_id")
