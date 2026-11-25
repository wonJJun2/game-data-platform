"""Drop the retired player counts, price history, and personal patch DM tables.

Revision ID: 4a7ed118ec33
Revises: 8f2c6e1a4b90
"""

from alembic import op
import sqlalchemy as sa


revision = "4a7ed118ec33"
down_revision = "8f2c6e1a4b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL drops each table's own indexes and constraints with the table.
    op.drop_table("patch_notification_outbox")
    op.drop_table("discord_game_subscriptions")
    op.drop_table("game_price_history")
    op.drop_table("player_counts")


def downgrade() -> None:
    """Recreate empty tables. Deleted rows and sequence positions require a backup."""
    # player_counts predates the Alembic baseline. Use its original ORM definition.
    op.create_table(
        "player_counts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.BigInteger(), sa.ForeignKey("games.game_id"), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_player_counts_game_collected_at",
        "player_counts",
        ["game_id", sa.text("collected_at DESC")],
    )

    op.create_table(
        "game_price_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.BigInteger(), sa.ForeignKey("games.game_id"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("price_status", sa.String(20), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("initial_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("final_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_game_price_history_game_changed_at",
        "game_price_history",
        ["game_id", sa.text("changed_at DESC")],
    )

    op.create_table(
        "discord_game_subscriptions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), sa.ForeignKey("games.game_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "guild_id", "discord_user_id", "game_id",
            name="uq_discord_game_subscriptions_guild_user_game",
        ),
    )

    # Revision 76b857e8d48e added delivery_attempt_count to the channel outbox only.
    op.create_table(
        "patch_notification_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("patch_id", sa.BigInteger(), sa.ForeignKey("game_patches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "patch_id", "guild_id", "discord_user_id",
            name="uq_patch_notification_outbox_delivery",
        ),
    )
    op.create_index(
        "idx_patch_notification_outbox_status_created",
        "patch_notification_outbox",
        ["status", "created_at"],
    )
