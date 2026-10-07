"""create steam news patch detection table

Revision ID: a916e4b8b372
Revises: 804cfe33e0e7
Create Date: 2026-10-07 19:59:13.579187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a916e4b8b372'
down_revision: Union[str, Sequence[str], None] = '804cfe33e0e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "steam_news_patch_detection",
        sa.Column(
            "news_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "is_patch",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "detection_reason",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "detector_version",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["news_id"],
            ["steam_news.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("news_id"),
    )


def downgrade() -> None:
    op.drop_table("steam_news_patch_detection")
