import logging

from game_data_platform.storage import get_games
from game_data_platform.news_collector import collect_news
from game_data_platform.overwatch_collector import (
    LOCALES,
    collect_overwatch_patch_notes,
)
from game_data_platform.pubg_collector import (
    collect_pubg_patch_notes,
)
from game_data_platform.patch_processor import (
    process_patch_detection,
)
from game_data_platform.patch_sync import (
    sync_game_patches,
)
from game_data_platform.patch_llm_processor import (
    run_patch_llm_processing,
)

logger = logging.getLogger(__name__)


def run_patch_pipeline(
    llm_process_limit: int = 0,
) -> dict:
    games = get_games()

    # 1. Steam News 수집
    steam_collection = collect_news(
        games,
        count=20,
    )

    # 2. Steam News에서 패치 감지
    steam_detection = process_patch_detection()

    # 3. Steam 외부 링크를 이용해
    #    PUBG 공식 한국어 Patch Notes 수집
    pubg_collection = (
        collect_pubg_patch_notes()
    )

    # 4. Blizzard 공식 Overwatch Patch Notes 수집
    overwatch_collection = (
        collect_overwatch_patch_notes()
    )

    # 5. 모든 소스를 공통 game_patches로 동기화
    patch_sync = sync_game_patches()

    # 6. 신규/변경 패치 번역 및 요약
    llm_processing = run_patch_llm_processing(
        process_limit=llm_process_limit,
    )

    # Collector별 수집 실패 건수 집계
    collection_failures = {
        "steam": len(games) - len(steam_collection),
        "pubg": pubg_collection["failed"],
        "overwatch": (
            len(LOCALES)
            - len(overwatch_collection["locales"])
        ),
    }

    result = {
        "steam_collection": steam_collection,
        "steam_detection": steam_detection,
        "pubg_collection": pubg_collection,
        "overwatch_collection": overwatch_collection,
        "patch_sync": patch_sync,
        "llm_processing": llm_processing,
        "collection_failures": collection_failures,
    }

    logger.info(
        "Patch pipeline result: %s",
        result,
    )

    return result


def main() -> None:
    print(run_patch_pipeline())