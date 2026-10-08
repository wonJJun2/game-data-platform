import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from game_data_platform.text_utils import (
    detect_content_language,
)

BASE_URL = "https://overwatch.blizzard.com"

PATCH_NOTE_URLS = {
    "ko-KR": f"{BASE_URL}/ko-kr/news/patch-notes/live/",
    "en-US": f"{BASE_URL}/en-us/news/patch-notes/live/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}



def parse_source_date(
    source_patch_id: str,
) -> date:
    match = re.fullmatch(
        r"patch-(\d{4}-\d{2}-\d{2})",
        source_patch_id,
    )

    if not match:
        raise ValueError(
            f"Invalid patch id: {source_patch_id}"
        )

    return date.fromisoformat(
        match.group(1)
    )


def get_patch_notes(
    locale: str,
) -> list[dict]:
    if locale not in PATCH_NOTE_URLS:
        raise ValueError(
            f"Unsupported locale: {locale}"
        )

    url = PATCH_NOTE_URLS[locale]

    response = httpx.get(
        url,
        headers=HEADERS,
        follow_redirects=True,
        timeout=20.0,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    results = []

    for patch in soup.select(
        ".PatchNotes-patch"
    ):
        anchor = patch.select_one(
            ".anchor[id]"
        )

        title_element = patch.select_one(
            ".PatchNotes-patchTitle"
        )

        label_element = patch.select_one(
            ".PatchNotes-labels"
        )

        if (
            anchor is None
            or title_element is None
            or label_element is None
        ):
            continue

        source_patch_id = anchor.get("id")

        if not source_patch_id:
            continue

        sections = patch.select(
            ".PatchNotes-section"
        )

        content_text = "\n\n".join(
            section.get_text(
                "\n",
                strip=True,
            )
            for section in sections
        )

        content_html = "\n".join(
            str(section)
            for section in sections
        )

        results.append(
            {
                "source_patch_id": (
                    source_patch_id
                ),
                "locale": locale,
                "source_date": (
                    parse_source_date(
                        source_patch_id
                    )
                ),
                "label_text": (
                    label_element.get_text(
                        " ",
                        strip=True,
                    )
                ),
                "title": (
                    title_element.get_text(
                        " ",
                        strip=True,
                    )
                ),
                "content_text": content_text,
                "content_html": content_html,
                "detected_language": (
                    detect_content_language(
                        content_text
                    )
                ),
                "source_url": url,
            }
        )

    return results