import logging

import httpx

from game_data_platform.pubg import (
    fetch_pubg_patch,
    find_pubg_news_url,
    is_pubg_patch_title,
)

from game_data_platform.storage import (
    get_detected_steam_patches,
    save_pubg_patch_note,
)

from game_data_platform.patch_detector import (
    DETECTOR_VERSION,
)

logger = logging.getLogger(__name__)


PUBG_STEAM_APP_ID = 578080


def collect_pubg_patch_notes() -> dict:
    steam_patches = (
        get_detected_steam_patches(
            DETECTOR_VERSION
        )
    )

    candidates = 0
    collected = 0
    unchanged = 0
    failed = 0

    for steam_patch in steam_patches:
        if (
            steam_patch["steam_app_id"]
            != PUBG_STEAM_APP_ID
        ):
            continue

        source_url = find_pubg_news_url(
            steam_patch["url"],
            steam_patch["contents"],
        )

        if source_url is None:
            continue

        candidates += 1

        try:
            patch = fetch_pubg_patch(
                source_url
            )

            if not is_pubg_patch_title(
                patch["title"]
            ):
                logger.info(
                    (
                        "Skip non-patch PUBG news: "
                        "%s | %s"
                    ),
                    patch["source_patch_id"],
                    patch["title"],
                )
                continue

            changed = (
                save_pubg_patch_note(
                    patch
                )
            )

            if changed:
                collected += 1

                logger.info(
                    (
                        "PUBG patch collected: "
                        "%s | %s"
                    ),
                    patch[
                        "source_patch_id"
                    ],
                    patch["title"],
                )
            else:
                unchanged += 1

        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
            ValueError,
        ) as error:
            failed += 1

            logger.exception(
                (
                    "PUBG patch collection "
                    "failed: %s"
                ),
                source_url,
            )

    result = {
        "candidates": candidates,
        "collected": collected,
        "unchanged": unchanged,
        "failed": failed,
    }

    logger.info(
        "PUBG collection result: %s",
        result,
    )

    return result