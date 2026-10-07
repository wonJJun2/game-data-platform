import logging

from game_data_platform import GAMES
from game_data_platform.news_collector import collect_news
from game_data_platform.patch_processor import process_patch_detection


logger = logging.getLogger(__name__)


def run_news_pipeline() -> dict:
    collection_results = collect_news(
        GAMES,
        count=20,
    )

    detection_result = process_patch_detection()

    fetched = sum(
        result["fetched"]
        for result in collection_results
    )

    inserted = sum(
        result["inserted"]
        for result in collection_results
    )

    result = {
        "games_processed": len(collection_results),
        "fetched": fetched,
        "inserted": inserted,
        "patch_detection": detection_result,
    }

    logger.info(
        "Steam news pipeline result: %s",
        result,
    )

    return result


def main() -> None:
    result = run_news_pipeline()
    print(result)