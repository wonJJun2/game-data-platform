"""Manage Discord users' Steam target-price subscriptions.

Price subscriptions are independent of patch subscriptions.
Only Korean Steam store prices (KRW) are supported for now.
"""

from sqlalchemy import delete, or_, select, func
from sqlalchemy.dialects.postgresql import insert

from game_data_platform.database import SessionLocal
from game_data_platform.models import DiscordPriceSubscription, Game


MAX_TARGET_PRICE_KRW = 999_999_999_999


def _validate_target_price(target_price: int) -> None:
    """Accept positive, whole-KRW target prices that fit NUMERIC(14, 2)."""
    if (
        type(target_price) is not int
        or target_price <= 0
        or target_price > MAX_TARGET_PRICE_KRW
    ):
        raise ValueError(
            "target_price must be a positive integer in KRW "
            f"(max {MAX_TARGET_PRICE_KRW})"
        )


def _validate_country_code(country_code: str) -> str:
    if not isinstance(country_code, str):
        raise ValueError("country_code must be KR")

    normalized = country_code.strip().upper()
    if normalized != "KR":
        raise ValueError("Only KR price subscriptions are supported")
    return normalized


def set_price_subscription(
    discord_user_id: int,
    game_id: int,
    target_price: int,
    country_code: str = "KR",
) -> bool:
    """Create/update a target price.

    Returns True if inserted, changed, or reactivated; False if already identical.
    Changing the target or reactivating the subscription rearms the alert.
    Calling repeatedly with the same target does NOT rearm the alert.
    `last_notified_at` is preserved as the last successful delivery timestamp.
    """
    _validate_target_price(target_price)
    country_code = _validate_country_code(country_code)

    statement = insert(DiscordPriceSubscription).values(
        discord_user_id=discord_user_id,
        game_id=game_id,
        country_code=country_code,
        target_price=target_price,
        is_active=True,
        is_armed=True,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_discord_price_subscriptions_user_game_country",
        set_={
            "target_price": statement.excluded.target_price,
            "is_active": True,
            "is_armed": True,
            "updated_at": func.now(),
        },
        where=or_(
            DiscordPriceSubscription.target_price.is_distinct_from(
                statement.excluded.target_price
            ),
            DiscordPriceSubscription.is_active.is_(False),
        ),
    ).returning(DiscordPriceSubscription.id)

    with SessionLocal.begin() as session:
        subscription_id = session.execute(statement).scalar_one_or_none()

    return subscription_id is not None


def get_price_subscriptions(
    discord_user_id: int,
) -> list[dict]:
    """Return active target-price subscriptions for a Discord user."""
    statement = (
        select(
            DiscordPriceSubscription.id.label("subscription_id"),
            Game.game_id,
            Game.steam_app_id,
            Game.name.label("game_name"),
            DiscordPriceSubscription.country_code,
            DiscordPriceSubscription.target_price,
            DiscordPriceSubscription.is_armed,
            DiscordPriceSubscription.last_notified_at,
            DiscordPriceSubscription.created_at,
            DiscordPriceSubscription.updated_at,
        )
        .join(
            Game,
            Game.game_id == DiscordPriceSubscription.game_id,
        )
        .where(
            DiscordPriceSubscription.discord_user_id == discord_user_id,
            DiscordPriceSubscription.is_active.is_(True),
        )
        .order_by(Game.name, Game.game_id)
    )

    with SessionLocal() as session:
        rows = session.execute(statement).mappings().all()

    return [dict(row) for row in rows]


def remove_price_subscription(
    discord_user_id: int,
    game_id: int,
    country_code: str = "KR",
) -> bool:
    """Remove a price subscription. Returns True only if a row was removed."""
    country_code = _validate_country_code(country_code)
    statement = (
        delete(DiscordPriceSubscription)
        .where(
            DiscordPriceSubscription.discord_user_id == discord_user_id,
            DiscordPriceSubscription.game_id == game_id,
            DiscordPriceSubscription.country_code == country_code,
        )
        .returning(DiscordPriceSubscription.id)
    )

    with SessionLocal.begin() as session:
        removed_id = session.execute(statement).scalar_one_or_none()

    return removed_id is not None
