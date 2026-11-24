"""Add price notification outbox and alert generation."""

from alembic import op
import sqlalchemy as sa

revision = "8f2c6e1a4b90"
down_revision = "c9f34b2e8a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discord_price_subscriptions",
        sa.Column("alert_generation", sa.BigInteger(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_price_subscription_generation",
        "discord_price_subscriptions", "alert_generation >= 1",
    )
    op.create_table(
        "discord_price_notification_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("discord_price_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_generation", sa.BigInteger(), nullable=False),
        sa.Column("target_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("initial_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("final_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("price_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivery_attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("subscription_id", "alert_generation", name="uq_price_outbox_subscription_generation"),
        sa.CheckConstraint("alert_generation >= 1", name="ck_price_outbox_generation"),
        sa.CheckConstraint("target_price > 0", name="ck_price_outbox_target_positive"),
        sa.CheckConstraint("final_price >= 0", name="ck_price_outbox_final_nonnegative"),
        sa.CheckConstraint("final_price <= target_price", name="ck_price_outbox_target_reached"),
    )
    op.create_index(
        "ix_discord_price_notification_outbox_ready",
        "discord_price_notification_outbox", ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_discord_price_notification_outbox_ready", table_name="discord_price_notification_outbox")
    op.drop_table("discord_price_notification_outbox")
    op.drop_constraint("ck_price_subscription_generation", "discord_price_subscriptions", type_="check")
    op.drop_column("discord_price_subscriptions", "alert_generation")
