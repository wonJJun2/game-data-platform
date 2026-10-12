import re


def detect_content_language(text: str) -> str:
    hangul_count = len(
        re.findall(r"[가-힣]", text)
    )

    english_count = len(
        re.findall(r"[A-Za-z]", text)
    )

    total = hangul_count + english_count

    if total == 0:
        return "unknown"

    hangul_ratio = hangul_count / total

    if hangul_ratio >= 0.1:
        return "ko"

    return "en"

import hashlib
import html
import re


def clean_patch_content(text: str) -> str:
    if not text:
        return ""

    cleaned = text

    # 구조를 보존해야 하는 BBCode
    cleaned = re.sub(
        r"\[(?:p|h1|h2|h3|h4)\]",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\[/(?:p|h1|h2|h3|h4)\]",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\[list(?:=[^\]]+)?\]",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\[/list\]",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\[\*\]",
        "\n- ",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\[/\*\]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # attribute가 포함된 나머지 BBCode 제거
    cleaned = re.sub(
        r"\[/?[a-zA-Z0-9_]+(?:=[^\]]+|\s+[^\]]*)?\]",
        "",
        cleaned,
    )

    cleaned = html.unescape(cleaned)

    # 공백 정리
    cleaned = re.sub(
        r"[ \t]+",
        " ",
        cleaned,
    )

    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    )

    return cleaned.strip()


def make_content_hash(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()