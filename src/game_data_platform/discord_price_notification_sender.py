"""Price alert message formatting and read-only delivery eligibility."""

import asyncio
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit

import discord
from sqlalchemy import func, select

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    Game,
    DiscordPriceSubscription,
    DiscordPriceNotificationOutbox,
)


def _validate_price(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"Invalid {field}")
    return value


def _format_krw(value: Decimal) -> str:
    # Do not silently round non-integral prices.
    formatted = format(value, ",f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return f"{formatted}원"


def _safe_image_url(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    if any(c.isspace() or ord(c) < 32 or c in '<>`\\' for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        ):
            # Access port to reject malformed ports.
            _ = parsed.port
            return value
    except ValueError:
        pass
    return None


def format_price_notification(delivery: dict) -> discord.Embed:
    """Build a DM embed from the outbox price snapshot and game metadata.

    Required keys: game_name, steam_app_id, currency, target_price,
    initial_price (nullable), final_price, discount_percent, price_checked_at.
    Optional key: header_image_url.
    Eligibility and ownership checks are performed separately before sending.
    """
    if delivery.get("currency") != "KRW":
        raise ValueError("Only KRW price notifications are supported")

    target = _validate_price(delivery.get("target_price"), "target_price")
    final = _validate_price(delivery.get("final_price"), "final_price")
    if target <= 0 or final > target:
        raise ValueError("Price does not meet a positive target price")

    initial = delivery.get("initial_price")
    if initial is not None:
        initial = _validate_price(initial, "initial_price")

    discount = delivery.get("discount_percent")
    if type(discount) is not int or not 0 <= discount <= 100:
        raise ValueError("Invalid discount_percent")

    app_id = delivery.get("steam_app_id")
    if type(app_id) is not int or app_id <= 0:
        raise ValueError("Invalid steam_app_id")

    checked_at = delivery.get("price_checked_at")
    if not isinstance(checked_at, datetime) or checked_at.utcoffset() is None:
        raise ValueError("price_checked_at must be timezone-aware")

    game_name = discord.utils.escape_mentions(
        discord.utils.escape_markdown(
            str(delivery.get("game_name") or "알 수 없는 게임")[:100]
        )
    )
    store_url = f"https://store.steampowered.com/app/{app_id}/"

    embed = discord.Embed(
        title="🎮 Steam 목표 가격 도달!",
        url=store_url,
        description=(
            f"**{game_name}**\n\n"
            "가격 확인 시점에 설정한 목표 가격 이하로 판매 중이었습니다."
        ),
        colour=discord.Colour.green(),
        timestamp=checked_at,
    )
    embed.add_field(
        name="정가",
        value=_format_krw(initial) if initial is not None else "정보 없음",
        inline=True,
    )
    embed.add_field(name="판매 가격", value=_format_krw(final), inline=True)
    embed.add_field(name="할인율", value=f"{discount}%", inline=False)
    embed.add_field(name="목표 가격", value=_format_krw(target), inline=False)
    embed.add_field(
        name="Steam 상점",
        value=f"[상점 바로가기]({store_url})",
        inline=False,
    )

    image_url = _safe_image_url(delivery.get("header_image_url"))
    if image_url is not None:
        embed.set_image(url=image_url)

    embed.set_footer(text="한국 Steam 스토어 기준 · 가격 확인 시각")
    return embed


class PriceDeliveryStale(Exception):
    """The outbox no longer exists or this worker does not own a valid lease."""


class PriceDeliveryNotEligible(Exception):
    """The owned job no longer matches the current subscription."""


def load_price_notification_delivery(
    notification_id: int,
    attempt_count: int,
) -> dict:
    """Read ownership, subscription and snapshot in a single DB statement.

    A read-only eligibility check is not a lock on a future Discord API call.
    The sender must invoke it again immediately before sending if it performs
    an asynchronous recipient lookup first.
    """
    if type(notification_id) is not int or notification_id < 1:
        raise ValueError("notification_id must be a positive integer")
    if type(attempt_count) is not int or attempt_count < 1:
        raise ValueError("attempt_count must be a positive integer")

    outbox = DiscordPriceNotificationOutbox
    subscription = DiscordPriceSubscription
    statement = (
        select(
            outbox.id.label("notification_id"),
            outbox.subscription_id,
            outbox.alert_generation,
            outbox.attempt_count,
            outbox.lease_until,
            outbox.target_price,
            outbox.initial_price,
            outbox.final_price,
            outbox.discount_percent,
            outbox.currency,
            outbox.price_checked_at,
            subscription.discord_user_id,
            subscription.country_code,
            subscription.is_active,
            subscription.is_armed,
            subscription.alert_generation.label("current_generation"),
            subscription.target_price.label("current_target_price"),
            Game.name.label("game_name"),
            Game.steam_app_id,
            Game.header_image_url,
        )
        .select_from(outbox)
        .join(subscription, subscription.id == outbox.subscription_id)
        .join(Game, Game.game_id == subscription.game_id)
        .where(
            outbox.id == notification_id,
            outbox.status == "processing",
            outbox.attempt_count == attempt_count,
            outbox.lease_until > func.clock_timestamp(),
        )
    )

    with SessionLocal() as session:
        row = session.execute(statement).mappings().one_or_none()

    if row is None:
        # A deleted subscription cascades to its outbox. There is then no
        # remaining job to cancel. Expired/reclaimed jobs must not be modified.
        raise PriceDeliveryStale("Outbox missing or worker ownership expired")

    delivery = dict(row)
    if not delivery["is_active"]:
        raise PriceDeliveryNotEligible("Subscription is inactive")
    if delivery["alert_generation"] != delivery["current_generation"]:
        raise PriceDeliveryNotEligible("Alert generation has changed")
    if delivery["target_price"] != delivery["current_target_price"]:
        raise PriceDeliveryNotEligible("Target price has changed")
    if delivery["is_armed"]:
        raise PriceDeliveryNotEligible("Subscription has been rearmed")
    if delivery["country_code"] != "KR" or delivery["currency"] != "KRW":
        raise PriceDeliveryNotEligible("Unsupported country or currency")
    if type(delivery["discord_user_id"]) is not int or delivery["discord_user_id"] <= 0:
        raise PriceDeliveryNotEligible("Invalid Discord recipient")

    return delivery


async def send_price_notification(client: discord.Client, notification: dict) -> int:
    """Send one owned price alert as a DM; no database writes here."""
    notification_id = notification["notification_id"]
    attempt_count = notification["attempt_count"]
    delivery = await asyncio.to_thread(
        load_price_notification_delivery, notification_id, attempt_count,
    )
    user_id = delivery["discord_user_id"]
    user = client.get_user(user_id)
    if user is None:
        user = await client.fetch_user(user_id)
    if user.id != user_id:
        raise PriceDeliveryNotEligible("Discord recipient mismatch")
    channel = await user.create_dm()
    if not isinstance(channel, discord.DMChannel) or channel.recipient is None or channel.recipient.id != user_id:
        raise PriceDeliveryNotEligible("Discord DM channel recipient mismatch")
    # Recipient/channel lookup may involve network I/O. Re-read the DB after it.
    delivery = await asyncio.to_thread(
        load_price_notification_delivery, notification_id, attempt_count,
    )
    if delivery["discord_user_id"] != user_id:
        raise PriceDeliveryNotEligible("Discord recipient changed")
    embed = format_price_notification(delivery)
    message = await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    return message.id
