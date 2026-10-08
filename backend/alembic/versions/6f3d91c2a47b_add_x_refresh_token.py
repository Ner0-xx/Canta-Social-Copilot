"""Add encrypted X OAuth refresh token storage.

Revision ID: 6f3d91c2a47b
Revises: 250578adc767
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6f3d91c2a47b"
down_revision: str | Sequence[str] | None = "250578adc767"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_connections",
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oauth_connections", "encrypted_refresh_token")
