"""create patch notification outbox

Revision ID: e0bb2456c70d
Revises: c71ca918158f
Create Date: 2026-11-02 23:15:18.981367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0bb2456c70d'
down_revision: Union[str, Sequence[str], None] = 'c71ca918158f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. Outbox 테이블 생성
    op.create_table(
        "patch_notification_outbox",
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
            "discord_user_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "next_attempt_at",
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
        sa.UniqueConstraint(
            "patch_id",
            "guild_id",
            "discord_user_id",
            name="uq_patch_notification_outbox_delivery",
        ),
    )

    # 2. Worker 조회용 인덱스
    op.create_index(
        "idx_patch_notification_outbox_status_created",
        "patch_notification_outbox",
        ["status", "created_at"],
    )

    # 3. 신규 패치 알림 작업 생성 함수
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

    # 4. game_patches INSERT 트리거
    op.execute("""
        CREATE TRIGGER trg_game_patch_notify_outbox
        AFTER INSERT ON game_patches
        FOR EACH ROW
        EXECUTE FUNCTION enqueue_game_patch_notifications();
    """)


def downgrade() -> None:
    # 생성 역순으로 제거
    op.execute("""
        DROP TRIGGER trg_game_patch_notify_outbox
        ON game_patches;
    """)

    op.execute("""
        DROP FUNCTION enqueue_game_patch_notifications();
    """)

    op.drop_index(
        "idx_patch_notification_outbox_status_created",
        table_name="patch_notification_outbox",
    )

    op.drop_table("patch_notification_outbox")

