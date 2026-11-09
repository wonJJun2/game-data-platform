
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    DiscordPatchChannel,
    DiscordPatchGameSubscription,
    Game,
)


def set_patch_channel(
    guild_id: int,
    channel_id: int,
) -> bool:
    """서버 패치 채널 등록 또는 변경.

    새로 등록하거나 채널이 변경되면 True.
    이미 같은 채널이면 False.
    """

    statement = insert(DiscordPatchChannel).values(
        guild_id=guild_id,
        channel_id=channel_id,
    )

    statement = (
        statement.on_conflict_do_update(
            index_elements=[DiscordPatchChannel.guild_id],
            set_={
                "channel_id": statement.excluded.channel_id,
                "updated_at": func.now(),
            },
            where=(
                DiscordPatchChannel.channel_id
                != statement.excluded.channel_id
            ),
        )
        .returning(DiscordPatchChannel.guild_id)
    )

    with SessionLocal.begin() as session:
        result = session.execute(
            statement
        ).scalar_one_or_none()

    return result is not None


SUPPORTED_PATCH_APP_IDS = frozenset({
    2357570,  # Overwatch
    578080,   # PUBG
})


def subscribe_patch_game(
    guild_id: int,
    game_id: int,
) -> bool:
    """서버의 패치 알림 게임 구독 등록.

    신규 등록이면 True, 중복이면 False.
    현재 Overwatch와 PUBG만 허용.
    """

    with SessionLocal.begin() as session:
        # 게임 존재 여부와 지원 대상 확인
        steam_app_id = session.execute(
            select(Game.steam_app_id).where(
                Game.game_id == game_id
            )
        ).scalar_one_or_none()

        if steam_app_id not in SUPPORTED_PATCH_APP_IDS:
            raise ValueError(
                "패치 알림은 현재 Overwatch와 PUBG만 지원합니다."
            )

        # 서버 단위 게임 구독 등록
        statement = (
            insert(DiscordPatchGameSubscription)
            .values(
                guild_id=guild_id,
                game_id=game_id,
            )
            .on_conflict_do_nothing(
                constraint=(
                    "uq_discord_patch_game_subscriptions_guild_game"
                )
            )
            .returning(DiscordPatchGameSubscription.id)
        )

        inserted_id = session.execute(
            statement
        ).scalar_one_or_none()

    return inserted_id is not None

def unsubscribe_patch_game(
    guild_id: int,
    game_id: int,
) -> bool:
    """서버의 패치 알림 게임 구독 해제.

    삭제했으면 True, 기존 구독이 없으면 False.
    """

    statement = (
        delete(DiscordPatchGameSubscription)
        .where(
            DiscordPatchGameSubscription.guild_id == guild_id,
            DiscordPatchGameSubscription.game_id == game_id,
        )
        .returning(DiscordPatchGameSubscription.id)
    )

    with SessionLocal.begin() as session:
        deleted_id = session.execute(
            statement
        ).scalar_one_or_none()

    return deleted_id is not None

def get_subscribed_patch_games(
    guild_id: int,
) -> list[dict]:
    """서버가 패치 알림을 구독 중인 게임 목록 조회."""

    statement = (
        select(
            Game.game_id,
            Game.steam_app_id,
            Game.name,
            DiscordPatchGameSubscription.created_at.label(
                "subscribed_at"
            ),
        )
        .select_from(DiscordPatchGameSubscription)
        .join(
            Game,
            DiscordPatchGameSubscription.game_id == Game.game_id,
        )
        .where(
            DiscordPatchGameSubscription.guild_id == guild_id
        )
        .order_by(Game.name)
    )

    with SessionLocal() as session:
        rows = session.execute(
            statement
        ).mappings().all()

        return [dict(row) for row in rows]

def get_patch_channel(
    guild_id: int,
) -> int | None:
    """서버에 설정된 패치 알림 채널 ID 조회.

    채널이 등록되어 있으면 channel_id 반환.
    등록되지 않았으면 None 반환.
    """

    statement = (
        select(DiscordPatchChannel.channel_id)
        .where(
            DiscordPatchChannel.guild_id == guild_id
        )
    )

    with SessionLocal() as session:
        return session.execute(
            statement
        ).scalar_one_or_none()
