import logging

import httpx
import psycopg

from game_data_platform.steam_price import (
    get_steam_price,
)
from game_data_platform.storage import (
    get_games,
    save_game_price,
)


logger = logging.getLogger(__name__)


def collect_game_prices(
    country_code: str = "KR",
) -> dict:
    games = get_games()

    result = {
        "total": len(games),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "retryable_failed": 0,
        "created": 0,
        "changed": 0,
        "checked": 0,
    }

    for game in games:
        steam_app_id = game["steam_app_id"]
        game_name = game["name"]

        try:
            price = get_steam_price(
                steam_app_id=steam_app_id,
                country_code=country_code,
            )

            save_result = save_game_price(
                price
            )

            action = save_result["action"]

            result["success"] += 1
            result[action] += 1

            logger.info(
                "Price collected | "
                "game=%s | "
                "app_id=%s | "
                "status=%s | "
                "price=%s | "
                "discount=%s | "
                "action=%s",
                game_name,
                steam_app_id,
                price["price_status"],
                price["final_price"],
                price["discount_percent"],
                action,
            )

        except httpx.TimeoutException:
            result["failed"] += 1
            result["retryable_failed"] += 1

            logger.exception(
                "Steam price timeout | "
                "game=%s | app_id=%s",
                game_name,
                steam_app_id,
            )

        except httpx.HTTPStatusError as error:
            result["failed"] += 1

            if error.response.status_code == 404:
                result["skipped"] += 1
            else:
                result["retryable_failed"] += 1

            logger.exception(
                "Steam price HTTP error | "
                "game=%s | "
                "app_id=%s | "
                "status=%s",
                game_name,
                steam_app_id,
                error.response.status_code,
            )

        except httpx.RequestError:
            result["failed"] += 1
            result["retryable_failed"] += 1

            logger.exception(
                "Steam price request error | "
                "game=%s | app_id=%s",
                game_name,
                steam_app_id,
            )

        except ValueError:
            result["failed"] += 1
            result["skipped"] += 1

            logger.exception(
                "Steam price data error | "
                "game=%s | app_id=%s",
                game_name,
                steam_app_id,
            )

        except psycopg.Error:
            result["failed"] += 1
            result["retryable_failed"] += 1

            logger.exception(
                "Price DB error | "
                "game=%s | app_id=%s",
                game_name,
                steam_app_id,
            )

        except Exception:
            result["failed"] += 1
            result["retryable_failed"] += 1

            logger.exception(
                "Unexpected price collector error | "
                "game=%s | app_id=%s",
                game_name,
                steam_app_id,
            )

    return result


def main() -> None:
    result = collect_game_prices()

    print(result)


if __name__ == "__main__":
    main()