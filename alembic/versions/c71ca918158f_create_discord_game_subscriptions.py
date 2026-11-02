"""create discord game subscriptions

Revision ID: c71ca918158f
Revises: 746e1c81b320
Create Date: 2026-11-02 22:29:09.747001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c71ca918158f'
down_revision: Union[str, Sequence[str], None] = '746e1c81b320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        "discord_game_subscriptions",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column(
            "guild_id",
            sa.BigInteger(),
            nullable=False,
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
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "guild_id",
            "discord_user_id",
            "game_id",
            name="uq_discord_game_subscriptions_guild_user_game",
        ),
    )


def downgrade() -> None:
    op.drop_table("discord_game_subscriptions")

