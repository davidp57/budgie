"""Add color_index to envelopes.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-26

Stores an optional palette index (0-7) for each envelope.
NULL means the UI picks a color automatically from the palette using
the envelope ID.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable color_index column to envelopes table."""
    op.add_column(
        "envelopes",
        sa.Column("color_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove color_index column from envelopes table."""
    op.drop_column("envelopes", "color_index")
