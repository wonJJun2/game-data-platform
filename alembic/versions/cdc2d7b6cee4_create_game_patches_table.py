"""create game patches table

Revision ID: cdc2d7b6cee4
Revises: 7a5093b788c1
Create Date: 2026-10-08 20:43:50.333031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdc2d7b6cee4'
down_revision: Union[str, Sequence[str], None] = '7a5093b788c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_patches",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "game_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "source_provider",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "source_key",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "source_locale",
            sa.String(length=10),
            nullable=True,
        ),
        sa.Column(
            "source_language",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "source_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "content_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_provider",
            "source_key",
            name="uq_game_patches_source",
        ),
    )

    op.create_index(
        "idx_game_patches_game_date",
        "game_patches",
        ["game_id", "source_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_game_patches_game_date",
        table_name="game_patches",
    )

    op.drop_table("game_patches")
