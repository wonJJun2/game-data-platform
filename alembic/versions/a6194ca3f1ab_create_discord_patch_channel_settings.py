"""create discord patch channel settings

Revision ID: a6194ca3f1ab
Revises: e0bb2456c70d
Create Date: 2026-11-09 22:00:11.528732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6194ca3f1ab'
down_revision: Union[str, Sequence[str], None] = 'e0bb2456c70d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. Discord 서버별 공용 패치 채널
    op.create_table(
        "discord_patch_channels",
        sa.Column(
            "guild_id",
            sa.BigInteger(),
            primary_key=True,
        ),
        sa.Column(
            "channel_id",
            sa.BigInteger(),
            nullable=False,
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
    )

    # 2. 서버별 게임 구독
    op.create_table(
        "discord_patch_game_subscriptions",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "guild_id",
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
            ["guild_id"],
            ["discord_patch_channels.guild_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.game_id"],
        ),
        sa.UniqueConstraint(
            "guild_id",
            "game_id",
            name="uq_discord_patch_game_subscriptions_guild_game",
        ),
    )

    # 3. 기존 개인 패치 DM Outbox 생성 트리거 제거
    op.execute("""
        DROP TRIGGER trg_game_patch_notify_outbox
        ON game_patches;
    """)

    op.execute("""
        DROP FUNCTION enqueue_game_patch_notifications();
    """)


def downgrade() -> None:
    # 1. 기존 개인 패치 DM 트리거 함수 복원
    op.execute("""
        CREATE FUNCTION enqueue_game_patch_notifications()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO patch_notification_outbox (
                patch_id,
                guild_id,
                discord_user_id
            )
            SELECT
                NEW.id,
                s.guild_id,
                s.discord_user_id
            FROM discord_game_subscriptions AS s
            WHERE s.game_id = NEW.game_id
            ON CONFLICT ON CONSTRAINT
                uq_patch_notification_outbox_delivery
            DO NOTHING;

            RETURN NEW;
        END;
        $$;
    """)

    # 2. 기존 개인 패치 DM 트리거 복원
    op.execute("""
        CREATE TRIGGER trg_game_patch_notify_outbox
        AFTER INSERT ON game_patches
        FOR EACH ROW
        EXECUTE FUNCTION enqueue_game_patch_notifications();
    """)

    # 3. 서버별 게임 구독 테이블 제거
    op.drop_table(
        "discord_patch_game_subscriptions"
    )

    # 4. 서버별 공용 패치 채널 테이블 제거
    op.drop_table(
        "discord_patch_channels"
    )
