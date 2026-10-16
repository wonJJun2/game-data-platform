"""create game price tables

Revision ID: 6d137a3448b1
Revises: 20db2e6e00ae
Create Date: 2026-10-16 14:51:02.635121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d137a3448b1'
down_revision: Union[str, Sequence[str], None] = '20db2e6e00ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_price_current",
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
            "provider",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "country_code",
            sa.String(length=2),
            nullable=False,
        ),
        sa.Column(
            "price_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "is_free",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=True,
        ),
        sa.Column(
            "initial_price",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "final_price",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "discount_percent",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "game_id",
            "provider",
            "country_code",
            name=(
                "uq_game_price_current_"
                "game_provider_country"
            ),
        ),
    )

    op.create_table(
        "game_price_history",
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
            "provider",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "country_code",
            sa.String(length=2),
            nullable=False,
        ),
        sa.Column(
            "price_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "is_free",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=True,
        ),
        sa.Column(
            "initial_price",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "final_price",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "discount_percent",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_index(
        "idx_game_price_history_game_changed_at",
        "game_price_history",
        [
            "game_id",
            sa.text("changed_at DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_game_price_history_game_changed_at",
        table_name="game_price_history",
    )

    op.drop_table(
        "game_price_history"
    )

    op.drop_table(
        "game_price_current"
    )
