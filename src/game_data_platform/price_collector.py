import logging

import httpx
import psycopg
from sqlalchemy import select

from game_data_platform.database import SessionLocal
from game_data_platform.discord_price_notification_service import (
    process_collected_price,
)
from game_data_platform.models import DiscordPriceSubscription, Game
from game_data_platform.steam_price import get_steam_price
from game_data_platform.storage import save_game_price


logger = logging.getLogger(__name__)


def get_subscribed_price_games(country_code: str = "KR") -> list[dict]:
    """Return each game once, even when multiple users subscribe to it."""
    active_subscription = (
        select(DiscordPriceSubscription.id)
        .where(
            DiscordPriceSubscription.game_id == Game.game_id,
            DiscordPriceSubscription.country_code == country_code,
            DiscordPriceSubscription.is_active.is_(True),
        )
        .exists()
    )
    statement = (
        select(Game.game_id, Game.steam_app_id, Game.name)
        .where(active_subscription)
        .order_by(Game.game_id)
    )
    with SessionLocal() as session:
        return [dict(row) for row in session.execute(statement).mappings().all()]


def collect_game_prices(country_code: str = "KR") -> dict:
    if not isinstance(country_code, str) or country_code.strip().upper() != "KR":
        raise ValueError("Only KR price subscriptions are supported")
    country_code = country_code.strip().upper()
    games = get_subscribed_price_games(country_code)

    result = {
        "total": len(games),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "retryable_failed": 0,
        "saved": 0,
        "created": 0,
        "changed": 0,
        "checked": 0,
        "evaluation_failed": 0,
        "superseded": 0,
        "subscriptions_scanned": 0,
        "enqueued": 0,
        "rearmed": 0,
        "kept": 0,
        "subscriptions_skipped": 0,
    }

    for game in games:
        steam_app_id = game["steam_app_id"]
        game_name = game["name"]

        # Phase 1: fetch a new observation. Never evaluate a cached price
        # after a request error.
        try:
            price = get_steam_price(
                steam_app_id=steam_app_id,
                country_code=country_code,
            )
        except httpx.TimeoutException:
            result["failed"] += 1
            result["retryable_failed"] += 1
            logger.exception("Steam price timeout | game=%s | app_id=%s", game_name, steam_app_id)
            continue
        except httpx.HTTPStatusError as error:
            result["failed"] += 1
            if error.response.status_code == 404:
                result["skipped"] += 1
            else:
                result["retryable_failed"] += 1
            logger.exception("Steam price HTTP error | game=%s | app_id=%s | status=%s", game_name, steam_app_id, error.response.status_code)
            continue
        except httpx.RequestError:
            result["failed"] += 1
            result["retryable_failed"] += 1
            logger.exception("Steam price request error | game=%s | app_id=%s", game_name, steam_app_id)
            continue
        except ValueError:
            result["failed"] += 1
            result["skipped"] += 1
            logger.exception("Steam price data error | game=%s | app_id=%s", game_name, steam_app_id)
            continue
        except Exception:
            result["failed"] += 1
            result["retryable_failed"] += 1
            logger.exception("Unexpected Steam price error | game=%s | app_id=%s", game_name, steam_app_id)
            continue

        # Phase 2: persist the observation before evaluating subscriptions.
        try:
            save_result = save_game_price(price)
            action = save_result["action"]
            if action not in ("created", "changed", "checked"):
                raise RuntimeError(f"Unknown price save action: {action}")
            result["saved"] += 1
            result[action] += 1
        except psycopg.Error:
            result["failed"] += 1
            result["retryable_failed"] += 1
            logger.exception("Price DB error | game=%s | app_id=%s", game_name, steam_app_id)
            continue
        except Exception:
            result["failed"] += 1
            result["retryable_failed"] += 1
            logger.exception("Price save error | game=%s | app_id=%s", game_name, steam_app_id)
            continue

        # Phase 3: evaluate the exact committed observation. This also handles
        # free/unavailable observations without changing armed state.
        try:
            evaluation = process_collected_price(
                current_id=save_result["current_id"],
                expected_checked_at=save_result["checked_at"],
            )
            observation_status = evaluation["observation_status"]
            if observation_status != "processed":
                if observation_status == "superseded":
                    result["superseded"] += 1
                raise RuntimeError(f"Price observation not processed: {observation_status}")

            result["subscriptions_scanned"] += evaluation["scanned"]
            result["enqueued"] += evaluation["enqueued"]
            result["rearmed"] += evaluation["rearmed"]
            result["kept"] += evaluation["kept"]
            result["subscriptions_skipped"] += evaluation["skipped"]
        except Exception:
            result["failed"] += 1
            result["retryable_failed"] += 1
            result["evaluation_failed"] += 1
            logger.exception("Price evaluation error | game=%s | app_id=%s", game_name, steam_app_id)
            continue

        result["success"] += 1
        logger.info(
            "Price collected | game=%s | app_id=%s | status=%s | "
            "price=%s | discount=%s | action=%s | enqueued=%s | rearmed=%s",
            game_name, steam_app_id, price["price_status"],
            price["final_price"], price["discount_percent"], action,
            evaluation["enqueued"], evaluation["rearmed"],
        )

    return result


def main() -> None:
    result = collect_game_prices()
    print(result)
    if result["retryable_failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
