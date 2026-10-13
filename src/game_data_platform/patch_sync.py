import logging

from game_data_platform.pubg import (
    find_pubg_news_url,
)

from game_data_platform.storage import (
    get_canonical_overwatch_patches,
    get_canonical_pubg_patches,
    get_detected_steam_patches,
    get_game_by_steam_app_id,
    save_game_patch,
)

from game_data_platform.patch_detector import (
    DETECTOR_VERSION,
)

from game_data_platform.text_utils import (
    detect_content_language,
)


logger = logging.getLogger(__name__)


OVERWATCH_STEAM_APP_ID = 2357570
PUBG_STEAM_APP_ID = 578080

def sync_steam_patches() -> int:
    patches = get_detected_steam_patches(
        DETECTOR_VERSION
    )

    synced = 0

    for patch in patches:
        if (
            patch["steam_app_id"]
            == PUBG_STEAM_APP_ID
            and find_pubg_news_url(
                patch["url"],
                patch["contents"],
            )
            is not None
        ):
            logger.info(
                (
                    "Skip PUBG official-link "
                    "patch from Steam sync: %s"
                ),
                patch["steam_gid"],
            )
            continue

        content_text = (
            patch["contents"] or ""
        )

        source_language = (
            detect_content_language(
                content_text
            )
        )

        data = {
            "game_id": patch["game_id"],
            "source_provider": "steam",
            "source_key": patch["steam_gid"],
            "source_locale": None,
            "source_language": source_language,
            "source_date": (
                patch["published_at"].date()
                if patch["published_at"]
                else None
            ),
            "published_at": (
                patch["published_at"]
            ),
            "title": patch["title"],
            "content_text": content_text,
            "source_url": patch["url"],
        }

        if save_game_patch(data):
            synced += 1

    return synced


def sync_overwatch_patches() -> int:
    game = get_game_by_steam_app_id(
        OVERWATCH_STEAM_APP_ID
    )

    if game is None:
        raise ValueError(
            "Overwatch game not found"
        )

    patches = (
        get_canonical_overwatch_patches()
    )

    synced = 0

    for patch in patches:
        data = {
            "game_id": game["game_id"],
            "source_provider": "blizzard",
            "source_key": (
                patch["source_patch_id"]
            ),
            "source_locale": (
                patch["locale"]
            ),
            "source_language": (
                patch["detected_language"]
            ),
            "source_date": (
                patch["source_date"]
            ),
            "published_at": None,
            "title": patch["title"],
            "content_text": (
                patch["content_text"]
            ),
            "source_url": (
                patch["source_url"]
            ),
        }

        if save_game_patch(data):
            synced += 1

    return synced


def sync_pubg_patches() -> int:
    game = get_game_by_steam_app_id(
        PUBG_STEAM_APP_ID
    )

    if game is None:
        raise ValueError(
            "PUBG game not found"
        )

    patches = (
        get_canonical_pubg_patches()
    )

    synced = 0

    for patch in patches:
        data = {
            "game_id": game["game_id"],
            "source_provider": "pubg",
            "source_key": (
                patch["source_patch_id"]
            ),
            "source_locale": (
                patch["locale"]
            ),
            "source_language": (
                patch["detected_language"]
            ),
            "source_date": (
                patch["source_date"]
            ),
            "published_at": None,
            "title": patch["title"],
            "content_text": (
                patch["content_text"]
            ),
            "source_url": (
                patch["source_url"]
            ),
        }

        if save_game_patch(data):
            synced += 1

    return synced

def sync_game_patches() -> dict:
    steam_synced = sync_steam_patches()

    pubg_synced = (
        sync_pubg_patches()
    )

    overwatch_synced = (
        sync_overwatch_patches()
    )

    result = {
        "steam_synced": steam_synced,
        "pubg_synced": pubg_synced,
        "overwatch_synced": (
            overwatch_synced
        ),
        "total_synced": (
            steam_synced
            + pubg_synced
            + overwatch_synced
        ),
    }

    logger.info(
        "Game patch sync result: %s",
        result,
    )

    return result


def main() -> None:
    print(sync_game_patches())