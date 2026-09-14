import httpx


def get_current_players(app_id: int) -> int:
    url = (
        "https://api.steampowered.com/"
        "ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    )

    response = httpx.get(
        url,
        params={"appid": app_id},
        timeout=10.0,
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]["player_count"]
