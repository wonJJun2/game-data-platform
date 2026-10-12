"""create game patch processing table

Revision ID: 2001f34d07f1
Revises: cdc2d7b6cee4
Create Date: 2026-10-12 21:26:46.115656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2001f34d07f1'
down_revision: Union[str, Sequence[str], None] = 'cdc2d7b6cee4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_patch_processing",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "patch_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "target_language",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "source_content_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "translation_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "translated_content",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "translation_provider",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "translation_model",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "translation_prompt_version",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "translated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "summary_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "summary_provider",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "summary_model",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "summary_prompt_version",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "summarized_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patch_id"],
            ["game_patches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "patch_id",
            "target_language",
            name="uq_game_patch_processing_target",
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "game_patch_processing"
    )
