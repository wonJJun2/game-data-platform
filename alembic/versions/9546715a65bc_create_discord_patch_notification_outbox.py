"""create discord patch notification outbox

Revision ID: 9546715a65bc
Revises: a6194ca3f1ab
Create Date: 2026-11-17 20:29:28.786508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9546715a65bc'
down_revision: Union[str, Sequence[str], None] = 'a6194ca3f1ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. 구독별 알림 시작 기준
    # NULL이면 아직 알림이 활성화되지 않은 구독
    op.add_column(
        "discord_patch_game_subscriptions",
        sa.Column(
            "start_after_patch_id",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    # 2. Discord 공용 패치 알림 Outbox
    op.create_table(
        "discord_patch_notification_outbox",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "patch_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "guild_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "lease_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["patch_id"],
            ["game_patches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["discord_patch_channels.guild_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "patch_id",
            "guild_id",
            name="uq_discord_patch_notification_outbox_patch_guild",
        ),
    )

    # 3. Worker의 전송 대기 작업 조회용 인덱스
    op.create_index(
        "ix_discord_patch_notification_outbox_ready",
        "discord_patch_notification_outbox",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discord_patch_notification_outbox_ready",
        table_name="discord_patch_notification_outbox",
    )

    op.drop_table(
        "discord_patch_notification_outbox"
    )

    op.drop_column(
        "discord_patch_game_subscriptions",
        "start_after_patch_id",
    )
