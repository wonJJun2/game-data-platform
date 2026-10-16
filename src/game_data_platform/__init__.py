import logging
from datetime import datetime, timezone

import httpx
import psycopg

from game_data_platform.steam import get_current_players
from game_data_platform.storage import (
    get_games,
    save_player_count,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def collect_game(game: dict) -> None:
    steam_app_id = game["steam_app_id"]

    player_count = get_current_players(
        steam_app_id
    )

    data = {
        "app_id": steam_app_id,
        "name": game["name"],
        "player_count": player_count,
        "collected_at": datetime.now(timezone.utc),
    }

    save_player_count(data)

    logger.info(
        "%s | app_id=%s | player_count=%s",
        game["name"],
        steam_app_id,
        player_count,
    )


def main() -> None:
    games = get_games()

    for game in games:
        try:
            collect_game(game)

        except ValueError as exc:
            logger.error(
                "게임 기준정보 오류 - %s (%s): %s",
                game["name"],
                game["steam_app_id"],
                exc,
            )

        except psycopg.Error as exc:
            logger.error(
                "DB 저장 실패 - %s (%s): %s",
                game["name"],
                game["steam_app_id"],
                exc,
            )

        except httpx.TimeoutException:
            logger.error(
                "%s | request timeout",
                game["name"],
            )

        except httpx.HTTPStatusError as error:
            logger.error(
                "%s | status_code=%s",
                game["name"],
                error.response.status_code,
            )

        except httpx.RequestError as error:
            logger.error(
                "%s | request_error=%s",
                game["name"],
                error,
            )