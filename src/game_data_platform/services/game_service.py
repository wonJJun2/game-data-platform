from urllib.parse import urlparse
import httpx

from game_data_platform.steam_price import (
    get_steam_price,
)
from game_data_platform.storage import (
    create_game,
    get_game_by_steam_app_id,
)

class InvalidSteamStoreUrlError(ValueError):
    pass

class SteamGameNotFoundError(ValueError):
    pass

class SteamGameLookupError(RuntimeError):
    pass

class GameAlreadyRegisteredError(
    ValueError
):
    def __init__(
        self,
        game_id: int,
    ):
        self.game_id = game_id

        super().__init__(
            "이미 등록된 게임입니다."
        )

def extract_steam_app_id(
    steam_url: str,
) -> int:
    value = steam_url.strip()

    if not value:
        raise InvalidSteamStoreUrlError(
            "Steam Store URL을 입력해주세요."
        )

    parsed = urlparse(value)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise InvalidSteamStoreUrlError(
            "올바른 Steam Store URL을 입력해주세요."
        )

    hostname = (
        parsed.hostname.lower()
        if parsed.hostname
        else ""
    )

    if hostname not in {
        "store.steampowered.com",
        "www.store.steampowered.com",
    }:
        raise InvalidSteamStoreUrlError(
            "Steam Store 게임 URL만 사용할 수 있습니다."
        )

    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if (
        len(path_parts) < 2
        or path_parts[0] != "app"
        or not path_parts[1].isdigit()
    ):
        raise InvalidSteamStoreUrlError(
            "Steam 게임 페이지 URL 형식이 아닙니다."
        )

    steam_app_id = int(
        path_parts[1]
    )

    if steam_app_id <= 0:
        raise InvalidSteamStoreUrlError(
            "올바른 Steam App ID가 아닙니다."
        )

    return steam_app_id

def get_game_registration_preview(
    steam_url: str,
) -> dict:
    steam_app_id = extract_steam_app_id(
        steam_url
    )

    existing_game = (
        get_game_by_steam_app_id(
            steam_app_id
        )
    )

    try:
        steam_data = get_steam_price(
            steam_app_id=steam_app_id,
        )

    except httpx.HTTPError as exc:
        raise SteamGameLookupError(
            "Steam 게임 정보를 불러오지 못했습니다."
        ) from exc

    except ValueError as exc:
        raise SteamGameLookupError(
            "Steam 응답을 처리하지 못했습니다."
        ) from exc


    if not steam_data.get("name"):
        raise SteamGameNotFoundError(
            "Steam에서 게임을 찾을 수 없습니다."
        )


    return {
        "steam_app_id":
            steam_app_id,

        "name":
            steam_data["name"],

        "header_image_url":
            steam_data.get(
                "header_image_url"
            ),

        "price_status":
            steam_data.get(
                "price_status"
            ),

        "initial_price":
            steam_data.get(
                "initial_price"
            ),

        "final_price":
            steam_data.get(
                "final_price"
            ),

        "discount_percent":
            steam_data.get(
                "discount_percent",
                0,
            ),

        "already_registered":
            existing_game is not None,

        "existing_game_id":
            (
                existing_game["game_id"]
                if existing_game
                else None
            ),
    }

def register_game(
    steam_app_id: int,
) -> dict:
    existing_game = (
        get_game_by_steam_app_id(
            steam_app_id
        )
    )

    if existing_game is not None:
        raise GameAlreadyRegisteredError(
            existing_game["game_id"]
        )


    try:
        steam_data = get_steam_price(
            steam_app_id=steam_app_id,
        )

    except httpx.HTTPError as exc:
        raise SteamGameLookupError(
            "Steam 게임 정보를 불러오지 못했습니다."
        ) from exc

    except ValueError as exc:
        raise SteamGameLookupError(
            "Steam 응답을 처리하지 못했습니다."
        ) from exc


    name = steam_data.get("name")

    if not name:
        raise SteamGameNotFoundError(
            "Steam에서 게임을 찾을 수 없습니다."
        )


    game = create_game(
        steam_app_id=steam_app_id,
        name=name,
        header_image_url=(
            steam_data.get(
                "header_image_url"
            )
        ),
    )

    return game