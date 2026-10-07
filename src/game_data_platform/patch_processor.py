import logging

from game_data_platform.patch_detector import (
    DETECTOR_VERSION,
    detect_patch,
)
from game_data_platform.storage import (
    get_undetected_steam_news,
    save_patch_detection,
)


logger = logging.getLogger(__name__)


def process_patch_detection() -> dict:
    news_list = get_undetected_steam_news(
        DETECTOR_VERSION,
    )

    total = len(news_list)
    patch_count = 0
    non_patch_count = 0

    for news in news_list:
        result = detect_patch(news)

        save_patch_detection(
            news_id=news["id"],
            is_patch=result["is_patch"],
            detection_reason=result["reason"],
            detector_version=DETECTOR_VERSION,
        )

        if result["is_patch"]:
            patch_count += 1
        else:
            non_patch_count += 1

    result = {
        "total": total,
        "patch": patch_count,
        "non_patch": non_patch_count,
        "detector_version": DETECTOR_VERSION,
    }

    logger.info("Patch detection result: %s", result)

    return result