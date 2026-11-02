from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    DiscordGameSubscription,
    Game,
)

def subscribe_game(
    guild_id: int,
    discord_user_id: int,
    game_id: int,
) -> bool:
    """게임 구독 등록. 신규 등록이면 True, 중복이면 False."""

    statement = (
        insert(DiscordGameSubscription)
        .values(
            guild_id=guild_id,
            discord_user_id=discord_user_id,
            game_id=game_id,
        )
        .on_conflict_do_nothing(
            constraint=(
                "uq_discord_game_subscriptions_guild_user_game"
            )
        )
        .returning(DiscordGameSubscription.id)
    )

    with SessionLocal.begin() as session:
        inserted_id = session.execute(
            statement
        ).scalar_one_or_none()

    return inserted_id is not None

def unsubscribe_game(
    guild_id: int,
    discord_user_id: int,
    game_id: int,
) -> bool:
    """구독 해제. 삭제했으면 True, 기존 구독이 없으면 False."""

    statement = (
        delete(DiscordGameSubscription)
        .where(
            DiscordGameSubscription.guild_id == guild_id,
            DiscordGameSubscription.discord_user_id == discord_user_id,
            DiscordGameSubscription.game_id == game_id,
        )
        .returning(DiscordGameSubscription.id)
    )

    with SessionLocal.begin() as session:
        deleted_id = session.execute(
            statement
        ).scalar_one_or_none()

    return deleted_id is not None


def get_subscribed_games(
    guild_id: int,
    discord_user_id: int,
) -> list[dict]:
    """특정 서버에서 사용자가 구독한 게임 목록 조회."""

    statement = (
        select(
            Game.game_id,
            Game.steam_app_id,
            Game.name,
            DiscordGameSubscription.created_at.label(
                "subscribed_at"
            ),
        )
        .select_from(DiscordGameSubscription)
        .join(
            Game,
            DiscordGameSubscription.game_id == Game.game_id,
        )
        .where(
            DiscordGameSubscription.guild_id == guild_id,
            DiscordGameSubscription.discord_user_id == discord_user_id,
        )
        .order_by(Game.name)
    )

    with SessionLocal() as session:
        rows = session.execute(
            statement
        ).mappings().all()

        return [dict(row) for row in rows]
