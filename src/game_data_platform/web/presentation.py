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