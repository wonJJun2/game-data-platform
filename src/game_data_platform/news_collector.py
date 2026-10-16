from datetime import datetime, timezone
import logging

import httpx
import psycopg

from game_data_platform.steam import get_news_for_app
from game_data_platform.storage import (
    get_games,
    save_steam_news,
)


logger = logging.getLogger(__name__)


def collect_news_for_game(
    game: dict,
    count: int = 20,
) -> dict:
    steam_app_id = game["steam_app_id"]

    news_items = get_news_for_app(
        app_id=steam_app_id,
        count=count,
    )

    collected_at = datetime.now(
        timezone.utc
    )

    inserted_count = 0

    for item in news_items:
        data = {
            "app_id": steam_app_id,
            "steam_gid": item["gid"],
            "title": item["title"],
            "url": item["url"],
            "is_external_url": item.get(
                "is_external_url",
                False,
            ),
            "author": item.get("author"),
            "contents": item.get("contents"),
            "feed_label": item.get(
                "feedlabel"
            ),
            "feed_name": item.get(
                "feedname"
            ),
            "feed_type": item.get(
                "feed_type"
            ),
            "published_at": (
                datetime.fromtimestamp(
                    item["date"],
                    tz=timezone.utc,
                )
            ),
            "tags": item.get(
                "tags",
                [],
            ),
            "collected_at": collected_at,
        }

        inserted = save_steam_news(
            data
        )

        if inserted:
            inserted_count += 1

    logger.info(
        "%s | fetched=%s | inserted=%s",
        game["name"],
        len(news_items),
        inserted_count,
    )

    return {
        "steam_app_id": steam_app_id,
        "name": game["name"],
        "fetched": len(news_items),
        "inserted": inserted_count,
    }

def collect_news(
    games: list[dict],
    count: int = 20,
) -> list[dict]:
    results = []

    for game in games:
        try:
            result = collect_news_for_game(
                game,
                count=count,
            )

            results.append(result)

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
                "%s | news request timeout",
                game["name"],
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "%s | news status_code=%s",
                game["name"],
                exc.response.status_code,
            )

        except httpx.RequestError as exc:
            logger.error(
                "%s | news request_error=%s",
                game["name"],
                exc,
            )

    return results

def main() -> None:
    games = get_games()

    results = collect_news(
        games,
        count=20,
    )

    for result in results:
        logger.info(
            "%s | fetched=%s | inserted=%s",
            result["name"],
            result["fetched"],
            result["inserted"],
        )