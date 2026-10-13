import re
from datetime import date
from urllib.parse import urlparse
import html
import httpx
from bs4 import BeautifulSoup


PUBG_ALLOWED_HOSTS = {
    "pubg.com",
    "www.pubg.com",
}

PUBG_BASE_URL = "https://pubg.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/155.0.0.0 "
        "Safari/537.36"
    )
}

def is_pubg_news_url(
    url: str | None,
) -> bool:
    if not url:
        return False

    try:
        extract_pubg_news_id(url)
    except ValueError:
        return False

    return True

def find_pubg_news_url(
    *values: str | None,
) -> str | None:
    for value in values:
        if not value:
            continue

        decoded = html.unescape(value)

        urls = re.findall(
            r'https?://[^\s"\]\']+',
            decoded,
        )

        for url in urls:
            url = url.rstrip(
                ".,);"
            )

            if is_pubg_news_url(url):
                return url

    return None

def is_pubg_patch_title(
    title: str | None,
) -> bool:
    if not title:
        return False

    normalized = title.lower()

    patch_keywords = (
        "patch notes",
        "patch note",
        "패치 노트",
        "패치노트",
    )

    return any(
        keyword in normalized
        for keyword in patch_keywords
    )

def is_pubg_patch_title(
    title: str | None,
) -> bool:
    if not title:
        return False

    normalized = title.lower()

    patch_keywords = (
        "patch notes",
        "patch note",
        "패치 노트",
        "패치노트",
    )

    return any(
        keyword in normalized
        for keyword in patch_keywords
    )

def extract_pubg_news_id(
    url: str,
) -> str:
    parsed = urlparse(url)

    hostname = (
        parsed.hostname or ""
    ).lower()

    if hostname not in PUBG_ALLOWED_HOSTS:
        raise ValueError(
            f"Unsupported PUBG host: {hostname}"
        )

    match = re.search(
        r"/news/(\d+)",
        parsed.path,
    )

    if not match:
        raise ValueError(
            f"PUBG news ID not found: {url}"
        )

    return match.group(1)


def build_korean_pubg_url(
    source_url: str,
) -> str:
    news_id = extract_pubg_news_id(
        source_url
    )

    return (
        f"{PUBG_BASE_URL}"
        f"/ko/news/{news_id}"
    )


def fetch_html(
    url: str,
) -> str:
    response = httpx.get(
        url,
        timeout=20,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    )

    response.raise_for_status()

    return response.text


def parse_source_date(
    text: str,
) -> date:
    match = re.search(
        r"(\d{4})\.(\d{2})\.(\d{2})",
        text,
    )

    if not match:
        raise ValueError(
            "PUBG patch date not found"
        )

    year, month, day = map(
        int,
        match.groups(),
    )

    return date(
        year,
        month,
        day,
    )


def parse_patch_detail(
    html: str,
    source_url: str,
) -> dict:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    header = soup.select_one(
        "article.detail-header"
    )

    if header is None:
        raise ValueError(
            "PUBG detail header not found"
        )

    title_element = header.select_one(
        ".detail-header__title"
    )

    if title_element is None:
        raise ValueError(
            "PUBG patch title not found"
        )

    title = title_element.get_text(
        " ",
        strip=True,
    )

    source_date = parse_source_date(
        header.get_text(
            "\n",
            strip=True,
        )
    )

    content_element = soup.select_one(
        (
            "article.content-template"
            ".news-detail__content-template"
        )
    )

    if content_element is None:
        raise ValueError(
            "PUBG patch content not found"
        )

    content_text = content_element.get_text(
        "\n",
        strip=True,
    )

    content_html = str(
        content_element
    )

    if not content_text:
        raise ValueError(
            "PUBG patch content is empty"
        )

    source_patch_id = extract_pubg_news_id(
        source_url
    )

    return {
        "source_patch_id": (
            source_patch_id
        ),
        "source_date": source_date,
        "title": title,
        "content_text": content_text,
        "content_html": content_html,
        "source_url": source_url,
        "locale": "ko-KR",
        "detected_language": "ko",
    }


def fetch_pubg_patch(
    steam_external_url: str,
) -> dict:
    korean_url = build_korean_pubg_url(
        steam_external_url
    )

    html = fetch_html(
        korean_url
    )

    return parse_patch_detail(
        html=html,
        source_url=korean_url,
    )