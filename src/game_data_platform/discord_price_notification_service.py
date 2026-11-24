from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    DiscordPriceNotificationOutbox,
    DiscordPriceSubscription,
    GamePriceCurrent,
)


def evaluate_price_alert(
    *,
    target_price: Decimal,
    is_active: bool,
    is_armed: bool,
    price: dict,
) -> str:
    """Return enqueue, rearm, keep, or skip without changing DB state."""
    if not is_active:
        return "skip"

    if (
        not isinstance(target_price, Decimal)
        or not target_price.is_finite()
        or target_price <= 0
    ):
        raise ValueError("Invalid target price")

    if price.get("country_code") != "KR":
        return "skip"
    if price.get("currency") != "KRW":
        return "skip"
    if price.get("price_status") != "priced":
        return "skip"
    if price.get("is_free") is not False:
        return "skip"

    current_price = price.get("final_price")
    if (
        not isinstance(current_price, Decimal)
        or not current_price.is_finite()
        or current_price < 0
    ):
        return "skip"

    if current_price <= target_price:
        return "enqueue" if is_armed else "keep"
    return "keep" if is_armed else "rearm"


def process_collected_price(
    *,
    current_id: int,
    expected_checked_at: datetime,
) -> dict:
    """Evaluate a committed Steam price observation, not an arbitrary cached price.

    The caller must supply the exact checked_at returned by a successful save.
    Lock the current price first, then active subscriptions in ID order.
    Outbox insertion and disarming commit together; any failure rolls back both.
    No external Discord calls are made here.
    """
    if (
        not isinstance(expected_checked_at, datetime)
        or expected_checked_at.utcoffset() is None
    ):
        raise ValueError("expected_checked_at must be timezone-aware")

    result = {
        "observation_status": "processed",
        "scanned": 0,
        "enqueued": 0,
        "rearmed": 0,
        "kept": 0,
        "skipped": 0,
    }

    with SessionLocal.begin() as session:
        current = session.scalars(
            select(GamePriceCurrent)
            .where(GamePriceCurrent.id == current_id)
            .with_for_update()
        ).one_or_none()

        if current is None:
            result["observation_status"] = "missing"
            return result

        if current.checked_at != expected_checked_at:
            result["observation_status"] = "superseded"
            return result

        if current.provider != "steam" or current.country_code != "KR":
            result["observation_status"] = "unsupported"
            return result

        price = {
            "country_code": current.country_code,
            "currency": current.currency,
            "price_status": current.price_status,
            "is_free": current.is_free,
            "final_price": current.final_price,
        }

        subscriptions = session.scalars(
            select(DiscordPriceSubscription)
            .where(
                DiscordPriceSubscription.game_id == current.game_id,
                DiscordPriceSubscription.country_code == current.country_code,
                DiscordPriceSubscription.is_active.is_(True),
            )
            .order_by(DiscordPriceSubscription.id)
            .with_for_update()
        ).all()

        for subscription in subscriptions:
            result["scanned"] += 1
            decision = evaluate_price_alert(
                target_price=subscription.target_price,
                is_active=subscription.is_active,
                is_armed=subscription.is_armed,
                price=price,
            )

            if decision == "enqueue":
                session.add(
                    DiscordPriceNotificationOutbox(
                        subscription_id=subscription.id,
                        alert_generation=subscription.alert_generation,
                        target_price=subscription.target_price,
                        initial_price=current.initial_price,
                        final_price=current.final_price,
                        discount_percent=current.discount_percent,
                        currency=current.currency,
                        price_checked_at=current.checked_at,
                    )
                )
                subscription.is_armed = False
                result["enqueued"] += 1
            elif decision == "rearm":
                subscription.is_armed = True
                subscription.alert_generation += 1
                result["rearmed"] += 1
            elif decision == "keep":
                result["kept"] += 1
            else:
                result["skipped"] += 1

        # A constraint violation must abort the entire transaction, not silently
        # disarm a subscription. The UNIQUE constraint is a defensive invariant.
        session.flush()

    return result
