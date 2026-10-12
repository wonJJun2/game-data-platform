"""add llm processing errors

Revision ID: 04e1c7079e99
Revises: 21fc543098bc
Create Date: 2026-10-12 22:16:20.417037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04e1c7079e99'
down_revision: Union[str, Sequence[str], None] = '21fc543098bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_patch_processing",
        sa.Column(
            "translation_error",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "game_patch_processing",
        sa.Column(
            "summary_error",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "game_patch_processing",
        "summary_error",
    )

    op.drop_column(
        "game_patch_processing",
        "translation_error",
    )