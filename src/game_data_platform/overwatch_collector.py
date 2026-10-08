import logging

import httpx
import psycopg

from game_data_platform.overwatch import (
    get_patch_notes,
)
from game_data_platform.storage import (
    save_overwatch_patch_note,
)


logger = logging.getLogger(__name__)


LOCALES = [
    "ko-KR",
    "en-US",
]


def collect_overwatch_patch_notes() -> dict:
    fetched = 0
    inserted = 0

    locale_results = []

    for locale in LOCALES:
        try:
            patch_notes = get_patch_notes(
                locale
            )

            locale_inserted = 0

            for patch_note in patch_notes:
                was_inserted = (
                    save_overwatch_patch_note(
                        patch_note
                    )
                )

                if was_inserted:
                    locale_inserted += 1

            fetched += len(patch_notes)
            inserted += locale_inserted

            locale_result = {
                "locale": locale,
                "fetched": len(patch_notes),
                "inserted": locale_inserted,
            }

            locale_results.append(
                locale_result
            )

            logger.info(
                "Overwatch patch notes: %s",
                locale_result,
            )

        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
            psycopg.Error,
            ValueError,
        ) as exc:
            logger.exception(
                "Failed to collect "
                "Overwatch patch notes "
                "locale=%s: %s",
                locale,
                exc,
            )

    result = {
        "fetched": fetched,
        "inserted": inserted,
        "locales": locale_results,
    }

    logger.info(
        "Overwatch collector result: %s",
        result,
    )

    return result


def main() -> None:
    print(
        collect_overwatch_patch_notes()
    )