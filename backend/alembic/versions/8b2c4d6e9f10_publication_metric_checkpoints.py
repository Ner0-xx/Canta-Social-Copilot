"""Add per-publication metric checkpoints.

Revision ID: 8b2c4d6e9f10
Revises: 6f3d91c2a47b
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8b2c4d6e9f10"
down_revision: str | Sequence[str] | None = "6f3d91c2a47b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publication_metric_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint", sa.String(length=8), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("reactions", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("reposts", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("is_late", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["publication_id"], ["platform_publications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "publication_id", "checkpoint", name="uq_publication_metric_checkpoint"
        ),
    )
    op.create_index(
        op.f("ix_publication_metric_snapshots_publication_id"),
        "publication_metric_snapshots",
        ["publication_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_publication_metric_snapshots_publication_id"),
        table_name="publication_metric_snapshots",
    )
    op.drop_table("publication_metric_snapshots")
