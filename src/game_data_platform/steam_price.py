from decimal import Decimal

import httpx


STEAM_APPDETAILS_URL = (
    "https://store.steampowered.com/api/appdetails"
)

DEFAULT_COUNTRY_CODE = "KR"


def normalize_price(
    raw_price: int | None,
) -> Decimal | None:
    if raw_price is None:
        return None

    return (
        Decimal(raw_price)
        / Decimal("100")
    ).quantize(
        Decimal("0.01")
    )


def get_steam_price(
    steam_app_id: int,
    country_code: str = DEFAULT_COUNTRY_CODE,
) -> dict:
    country_code = (
        country_code
        .strip()
        .upper()
    )

    if len(country_code) != 2:
        raise ValueError(
            "country_code must be a 2-letter code"
        )

    response = httpx.get(
        STEAM_APPDETAILS_URL,
        params={
            "appids": steam_app_id,
            "cc": country_code.lower(),
            "l": "korean",
        },
        timeout=20.0,
    )

    response.raise_for_status()

    payload = response.json()

    app_payload = payload.get(
        str(steam_app_id)
    )

    if app_payload is None:
        raise ValueError(
            f"Invalid Steam response: {steam_app_id}"
        )

    if app_payload.get("success") is not True:
        return {
            "steam_app_id": steam_app_id,
            "name": None,
            "header_image_url": None,
            "provider": "steam",
            "country_code": country_code,
            "price_status": "unavailable",
            "is_free": False,
            "currency": None,
            "initial_price": None,
            "final_price": None,
            "discount_percent": 0,
        }

    data = (
        app_payload.get("data")
        or {}
    )

    name = data.get("name")
    header_image_url = data.get(
        "header_image"
    )

    is_free = bool(
        data.get("is_free")
    )

    price_overview = data.get(
        "price_overview"
    )

    if is_free:
        return {
            "steam_app_id": steam_app_id,
            "name": name,
            "header_image_url": header_image_url,
            "provider": "steam",
            "country_code": country_code,
            "price_status": "free",
            "is_free": True,
            "currency": None,
            "initial_price": None,
            "final_price": None,
            "discount_percent": 0,
        }

    if price_overview is None:
        return {
            "steam_app_id": steam_app_id,
            "name": name,
            "header_image_url": header_image_url,
            "provider": "steam",
            "country_code": country_code,
            "price_status": "unavailable",
            "is_free": False,
            "currency": None,
            "initial_price": None,
            "final_price": None,
            "discount_percent": 0,
        }

    return {
        "steam_app_id": steam_app_id,
        "name": name,
        "header_image_url": header_image_url,
        "provider": "steam",
        "country_code": country_code,
        "price_status": "priced",
        "is_free": False,
        "currency": (
            price_overview.get("currency")
        ),
        "initial_price": normalize_price(
            price_overview.get("initial")
        ),
        "final_price": normalize_price(
            price_overview.get("final")
        ),
        "discount_percent": int(
            price_overview.get(
                "discount_percent",
                0,
            )
        ),
    }