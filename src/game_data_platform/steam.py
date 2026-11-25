import httpx


def get_news_for_app(
    app_id: int,
    count: int = 20,
) -> list[dict]:
    url = (
        "https://api.steampowered.com/"
        "ISteamNews/GetNewsForApp/v2/"
    )

    response = httpx.get(
        url,
        params={
            "appid": app_id,
            "count": count,
            "maxlength": 0,
        },
        timeout=10.0,
    )

    response.raise_for_status()

    data = response.json()

    return data["appnews"].get("newsitems", [])