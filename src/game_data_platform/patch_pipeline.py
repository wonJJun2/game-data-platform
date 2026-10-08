import logging

from game_data_platform import GAMES
from game_data_platform.news_collector import collect_news
from game_data_platform.overwatch_collector import (
    collect_overwatch_patch_notes,
)
from game_data_platform.patch_processor import (
    process_patch_detection,
)
from game_data_platform.patch_sync import (
    sync_game_patches,
)


logger = logging.getLogger(__name__)


def run_patch_pipeline() -> dict:
    # 1. Steam News 수집
    steam_collection = collect_news(
        GAMES,
        count=20,
    )

    # 2. Steam News에서 패치 감지
    steam_detection = process_patch_detection()

    # 3. Blizzard 공식 Overwatch Patch Notes 수집
    overwatch_collection = (
        collect_overwatch_patch_notes()
    )

    # 4. 모든 소스를 공통 game_patches로 동기화
    patch_sync = sync_game_patches()

    result = {
        "steam_collection": steam_collection,
        "steam_detection": steam_detection,
        "overwatch_collection": (
            overwatch_collection
        ),
        "patch_sync": patch_sync,
    }

    logger.info(
        "Patch pipeline result: %s",
        result,
    )

    return result


def main() -> None:
    print(run_patch_pipeline())