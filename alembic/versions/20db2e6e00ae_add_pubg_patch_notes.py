"""add pubg patch notes

Revision ID: 20db2e6e00ae
Revises: 04e1c7079e99
Create Date: 2026-10-13 22:32:33.614099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20db2e6e00ae'
down_revision: Union[str, Sequence[str], None] = '04e1c7079e99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pubg_patch_notes",
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
            name="uq_pubg_patch_source_locale",
        ),
    )


def downgrade() -> None:
    op.drop_table("pubg_patch_notes")
