import re

def _looks_like_heading(
    line: str,
) -> bool:
    if len(line) > 80:
        return False

    if line.endswith(
        (
            ".",
            "!",
            "?",
            ";",
        )
    ):
        return False

    if line.startswith(
        (
            "http://",
            "https://",
        )
    ):
        return False

    # 날짜 / 시간 / 수치가 많이 포함된 줄은
    # 제목보다는 실제 패치 내용일 가능성이 높다.
    digit_count = sum(
        char.isdigit()
        for char in line
    )

    if digit_count >= 2:
        return False

    # 너무 긴 문장은 제목으로 보지 않는다.
    if len(line.split()) > 10:
        return False

    return True


def build_patch_blocks(
    text: str | None,
) -> list[dict]:
    if not text:
        return []

    blocks = []
    bullet_items = []

    def flush_bullets() -> None:
        nonlocal bullet_items

        if not bullet_items:
            return

        blocks.append(
            {
                "type": "list",
                "items": bullet_items,
            }
        )

        bullet_items = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            flush_bullets()
            continue

        if line.startswith(
            (
                "- ",
                "• ",
                "* ",
            )
        ):
            bullet_items.append(
                line[2:].strip()
            )
            continue

        flush_bullets()

        if _looks_like_heading(line):
            blocks.append(
                {
                    "type": "heading",
                    "text": line,
                }
            )
        else:
            blocks.append(
                {
                    "type": "paragraph",
                    "text": line,
                }
            )

    flush_bullets()

    return blocks


def build_summary_items(
    text: str | None,
) -> list[str]:
    if not text:
        return []

    items = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith(
            (
                "- ",
                "• ",
                "* ",
            )
        ):
            line = line[2:].strip()

        items.append(line)

    return items

def format_patch_date(
    value,
) -> str:
    if value is None:
        return "날짜 정보 없음"

    return value.strftime(
        "%Y.%m.%d"
    )

GAME_TITLE_ALIASES = {
    "Counter-Strike 2": (
        "Counter-Strike 2",
        "카운터-스트라이크 2",
        "CS2",
    ),
    "Apex 레전드": (
        "Apex 레전드",
        "Apex Legends",
        "에이펙스 레전드",
    ),
    "마블 라이벌즈": (
        "마블 라이벌즈",
        "Marvel Rivals",
    ),
    "Overwatch": (
        "Overwatch",
        "오버워치",
    ),
    "PUBG": (
        "PUBG",
        "배틀그라운드",
        "PUBG: BATTLEGROUNDS",
    ),
    "Dota 2": (
        "Dota 2",
        "도타 2",
    ),
    "THE FINALS": (
        "THE FINALS",
        "더 파이널스",
    ),
    "The First Descendant": (
        "The First Descendant",
        "퍼스트 디센던트",
    ),
}


TITLE_TERM_REPLACEMENTS = (
    (
        r"\bPatch Notes\b",
        "패치 노트",
    ),
    (
        r"\bPatch Note\b",
        "패치 노트",
    ),
    (
        r"\bVersion\b",
        "버전",
    ),
    (
        r"\bUpdate\b",
        "업데이트",
    ),
    (
        r"\bHotfix\b",
        "핫픽스",
    ),
)


def normalize_patch_title(
    game_name: str,
    translated_title: str | None,
    original_title: str,
) -> str:
    title = (
        translated_title
        or original_title
    ).strip()

    aliases = GAME_TITLE_ALIASES.get(
        game_name,
        (game_name,),
    )

    normalized_title = title

    # 제목 맨 앞의 게임명을
    # games.name 기준으로 통일
    for alias in aliases:
        if not normalized_title.lower().startswith(
            alias.lower()
        ):
            continue

        remainder = normalized_title[
            len(alias):
        ].lstrip(
            " :-–—"
        )

        if not remainder:
            normalized_title = game_name
        else:
            normalized_title = (
                f"{game_name} {remainder}"
            )

        break

    # 패치 제목에서 자주 등장하는
    # 영문 용어를 한국어로 통일
    for pattern, replacement in (
        TITLE_TERM_REPLACEMENTS
    ):
        normalized_title = re.sub(
            pattern,
            replacement,
            normalized_title,
            flags=re.IGNORECASE,
        )

    # 혹시 치환 과정에서 공백이 중복되면 정리
    normalized_title = re.sub(
        r"\s+",
        " ",
        normalized_title,
    ).strip()

    return normalized_title