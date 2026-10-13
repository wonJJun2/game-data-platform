import re

DETECTOR_VERSION = "v2"

EXCLUDE_TITLE_KEYWORDS = [
    "schedule",
    "preview",
    "roadmap",
    "anti cheat team",
    "anti-cheat team",
    "store update",
    "map service report",
]

STRONG_TITLE_KEYWORDS = [
    "patch notes",
    "gameplay patch",
    "hotfix",
]

CONTENT_PATCH_KEYWORDS = [
    "fixed:",
    "adjusted:",
    "changed:",
    "added:",
    "removed:",
    "nerfed",
    "buffed",
]


def detect_patch(news: dict) -> dict:
    title = news.get("title", "").lower()
    contents = news.get("contents", "").lower()
    feed_name = news.get("feed_name", "").lower()

    tags = [
        str(tag).lower()
        for tag in news.get("tags", [])
    ]

    # 1. 명확한 제외 제목
    for keyword in EXCLUDE_TITLE_KEYWORDS:
        if keyword in title:
            return {
                "is_patch": False,
                "reason": f"excluded title keyword: {keyword}",
            }

    # 2. Steam의 명시적 patchnotes 태그
    if "patchnotes" in tags:
        return {
            "is_patch": True,
            "reason": "patchnotes tag",
        }

    # 3. 외부 기사 제외
    if feed_name != "steam_community_announcements":
        return {
            "is_patch": False,
            "reason": f"non-official feed: {feed_name}",
        }

    # 4. 강한 제목 신호
    for keyword in STRONG_TITLE_KEYWORDS:
        if keyword in title:
            return {
                "is_patch": True,
                "reason": f"title keyword: {keyword}",
            }

    # Patch 1.4.4
    if re.search(r"\bpatch\s+\d", title):
        return {
            "is_patch": True,
            "reason": "patch version pattern",
        }

    # Update 11.12.0
    if re.search(r"\bupdate\s+\d+(?:\.\d+)+", title):
        return {
            "is_patch": True,
            "reason": "update version pattern",
        }

    # Latest Update + 실제 변경 내용
    if "update" in title:
        for keyword in CONTENT_PATCH_KEYWORDS:
            if keyword in contents:
                return {
                    "is_patch": True,
                    "reason": (
                        f"update title + content keyword: {keyword}"
                    ),
                }

    return {
        "is_patch": False,
        "reason": "no patch signal",
    }