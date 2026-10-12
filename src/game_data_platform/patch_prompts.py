import re

TRANSLATION_PROMPT_VERSION = "v3"
SUMMARY_PROMPT_VERSION = "v2"

TRANSLATION_SYSTEM_INSTRUCTION = """
You are a professional game patch note translator.

Translate game patch notes accurately into Korean.

Rules:
- Never change numbers, percentages, version numbers, or units.
- Never reverse the meaning of buffs, nerfs, increases, or decreases.
- Preserve game names, character names, skill names, weapon names,
  map names, and other proper nouns when an official Korean term
  is uncertain.
- Preserve headings, bullet points, and section structure.
- Do not summarize or omit content.
- Do not add explanations that are not present in the source.
- Output exactly in the requested format.
- Preserve all numeric values exactly.
- Dates may be naturally localized into Korean,
  but the year, month, day, time, timezone,
  and their meaning must not change.
- Preserve time values, version strings,
  percentages, and units exactly.
""".strip()


SUMMARY_SYSTEM_INSTRUCTION = """
You summarize game patch notes for Korean players.

Rules:
- Use only information present in the patch note.
- Do not invent changes, reasons, or explanations.
- Preserve important numbers when they affect gameplay.
- Prioritize information in this order:
  1. Major gameplay or balance changes
  2. New game modes, maps, heroes, weapons, or systems
  3. Important bug fixes and optimizations
  4. Time-limited events and meaningful rewards
  5. Story, cosmetic, store, or promotional content
- Deprioritize marketing language and promotional wording.
- When space is limited, omit lower-priority cosmetic or story content first.
- Preserve technical meaning such as latency, cooldown,
  damage, range, duration, percentages, and other gameplay terms.
- Write concise Korean.
- Use 3 to 7 bullet points.
- Each bullet should contain one clear topic.
- Do not include introductory or closing commentary.
""".strip()


def build_translation_prompt(
    game_name: str,
    title: str,
    content: str,
) -> str:
    return f"""
Game: {game_name}

Translate both the title and the FULL patch note into Korean.

You MUST return exactly two XML-style blocks.
Do not use Markdown code fences.
Do not write any text before or after the blocks.

Required output format:

<TITLE>
translated title
</TITLE>
<CONTENT>
translated full patch note
</CONTENT>

Original title:
{title}

Original patch note:
{content}
""".strip()


def build_summary_prompt(
    game_name: str,
    title: str,
    content: str,
) -> str:
    return f"""
Game: {game_name}
Patch title: {title}

Summarize the following Korean patch note for a player who wants
to understand the important changes quickly.

--- PATCH NOTE ---
{content}
--- END PATCH NOTE ---
""".strip()


def parse_translation_response(
    response: str,
) -> tuple[str, str]:
    cleaned = response.strip()

    # 모델이 Markdown code fence로 감싸는 경우 제거
    cleaned = re.sub(
        r"^```(?:xml|html|text)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    title_match = re.search(
        r"<\s*TITLE\s*>\s*(.*?)\s*<\s*/\s*TITLE\s*>",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    content_match = re.search(
        r"<\s*CONTENT\s*>\s*(.*?)\s*<\s*/\s*CONTENT\s*>",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if title_match and content_match:
        return (
            title_match.group(1).strip(),
            content_match.group(1).strip(),
        )

    # 간혹 태그 대신 TITLE: / CONTENT: 형식으로
    # 반환하는 경우까지 허용
    fallback_match = re.search(
        r"""
        TITLE\s*:\s*
        (.*?)
        \n+
        CONTENT\s*:\s*
        (.*)
        """,
        cleaned,
        flags=(
            re.IGNORECASE
            | re.DOTALL
            | re.VERBOSE
        ),
    )

    if fallback_match:
        return (
            fallback_match.group(1).strip(),
            fallback_match.group(2).strip(),
        )

    preview = cleaned[:1000]

    raise ValueError(
        "Invalid translation response format. "
        f"Response preview: {preview!r}"
    )