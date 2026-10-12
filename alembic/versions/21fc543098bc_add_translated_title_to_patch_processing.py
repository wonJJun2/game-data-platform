"""add translated title to patch processing

Revision ID: 21fc543098bc
Revises: 2001f34d07f1
Create Date: 2026-10-12 21:34:37.197047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21fc543098bc'
down_revision: Union[str, Sequence[str], None] = '2001f34d07f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_patch_processing",
        sa.Column(
            "translated_title",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "game_patch_processing",
        "translated_title",
    )
