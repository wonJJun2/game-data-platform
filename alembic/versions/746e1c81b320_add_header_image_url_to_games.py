"""add header image url to games

Revision ID: 746e1c81b320
Revises: 6d137a3448b1
Create Date: 2026-10-16 15:43:23.994123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '746e1c81b320'
down_revision: Union[str, Sequence[str], None] = '6d137a3448b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column(
            "header_image_url",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "games",
        "header_image_url",
    )
