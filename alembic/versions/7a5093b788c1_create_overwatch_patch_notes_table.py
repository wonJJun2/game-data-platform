"""create overwatch patch notes table

Revision ID: 7a5093b788c1
Revises: a916e4b8b372
Create Date: 2026-10-08 20:34:14.659647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a5093b788c1'
down_revision: Union[str, Sequence[str], None] = 'a916e4b8b372'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "overwatch_patch_notes",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "source_patch_id",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "locale",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "source_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "label_text",
            sa.Text(),
            nullable=False,
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
            "content_html",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "detected_language",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_patch_id",
            "locale",
            name="uq_overwatch_patch_source_locale",
        ),
    )


def downgrade() -> None:
    op.drop_table("overwatch_patch_notes")
