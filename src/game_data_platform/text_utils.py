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