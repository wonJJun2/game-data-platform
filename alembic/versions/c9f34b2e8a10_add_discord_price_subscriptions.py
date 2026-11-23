"""Add Discord price subscriptions.

Revision ID: c9f34b2e8a10
Revises: 76b857e8d48e
"""

from alembic import op
import sqlalchemy as sa


revision = "c9f34b2e8a10"
down_revision = "76b857e8d48e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discord_price_subscriptions",

        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),

        sa.Column(
            "discord_user_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "game_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "country_code",
            sa.String(length=2),
            server_default=sa.text("'KR'"),
            nullable=False,
        ),

        sa.Column(
            "target_price",
            sa.Numeric(14, 2),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),

        sa.Column(
            "is_armed",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),

        sa.Column(
            "last_notified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
        ),

        sa.UniqueConstraint(
            "discord_user_id",
            "game_id",
            "country_code",
            name="uq_discord_price_subscriptions_user_game_country",
        ),

        sa.CheckConstraint(
            "target_price > 0",
            name="ck_discord_price_subscriptions_target_price_positive",
        ),
    )


def downgrade() -> None:
    op.drop_table("discord_price_subscriptions")
