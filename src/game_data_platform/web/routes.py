from math import ceil
from pathlib import Path
from urllib.parse import urlencode
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    RedirectResponse,
)
from game_data_platform.storage import (
    get_current_game_price,
    get_game,
    get_games,
    get_patch_viewer_count,
    get_patch_viewer_detail,
    get_patch_viewer_games,
    get_patch_viewer_list,
)

from game_data_platform.services.game_service import (
    GameAlreadyRegisteredError,
    InvalidSteamStoreUrlError,
    SteamGameLookupError,
    SteamGameNotFoundError,
    get_game_registration_preview,
    register_game,
)

from game_data_platform.text_utils import (
    clean_patch_content,
)

from game_data_platform.web.presentation import (
    build_patch_blocks,
    build_summary_items,
    format_patch_date,
    normalize_patch_title,
)
from game_data_platform.patch_llm_processor import (
    process_patch_by_id,
)

router = APIRouter()


PACKAGE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=PACKAGE_DIR / "templates",
)

@router.get(
    "/games",
    response_class=HTMLResponse,
)
def game_list(
    request: Request,
    steam_url: str | None = None,
):
    games = get_games()

    registration_preview = None
    registration_error = None


    if steam_url:
        try:
            registration_preview = (
                get_game_registration_preview(
                    steam_url
                )
            )

        except (
            InvalidSteamStoreUrlError,
            SteamGameNotFoundError,
            SteamGameLookupError,
        ) as exc:
            registration_error = str(exc)


    return templates.TemplateResponse(
        request=request,
        name="games.html",
        context={
            "page_title": (
                "Game Data Viewer"
            ),
            "games": games,
            "total_count": len(games),
            "steam_url": steam_url or "",
            "registration_preview":
                registration_preview,
            "registration_error":
                registration_error,
        },
    )

@router.post(
    "/games/register",
)
def register_game_route(
    steam_app_id: int = Form(...),
):
    try:
        game = register_game(
            steam_app_id=steam_app_id,
        )

    except GameAlreadyRegisteredError as exc:
        return RedirectResponse(
            url=f"/games/{exc.game_id}",
            status_code=303,
        )

    except (
        SteamGameNotFoundError,
        SteamGameLookupError,
    ):
        return RedirectResponse(
            url="/games",
            status_code=303,
        )


    return RedirectResponse(
        url=f"/games/{game['game_id']}",
        status_code=303,
    )

@router.get(
    "/games/{game_id}",
    response_class=HTMLResponse,
    name="game_detail",
)
def game_detail(
    request: Request,
    game_id: int,
):
    game = get_game(
        game_id=game_id,
    )

    if game is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "page_title": (
                    "게임을 찾을 수 없습니다"
                ),
            },
            status_code=404,
        )

    current_price = get_current_game_price(
        game_id=game_id,
    )
    price_view = {
        "status": "not_collected",
        "label": "가격 정보 없음",
        "final_price": None,
        "initial_price": None,
        "discount_percent": 0,
        "checked_at": None,
    }

    if current_price is not None:
        price_status = current_price[
            "price_status"
        ]

        price_view["status"] = price_status
        price_view["checked_at"] = (
            current_price["checked_at"]
        )

        if price_status == "free":
            price_view["label"] = "무료"

        elif price_status == "priced":
            final_price = current_price[
                "final_price"
            ]
            initial_price = current_price[
                "initial_price"
            ]

            price_view["final_price"] = (
                f"{final_price:,.0f}"
                if final_price is not None
                else None
            )

            price_view["initial_price"] = (
                f"{initial_price:,.0f}"
                if initial_price is not None
                else None
            )

            price_view["discount_percent"] = (
                current_price[
                    "discount_percent"
                ]
            )

            if price_view["final_price"]:
                price_view["label"] = (
                    f"₩{price_view['final_price']}"
                )

        elif price_status == "unavailable":
            price_view["label"] = (
                "가격 정보 없음"
            )

    patches = get_patch_viewer_list(
        limit=5,
        offset=0,
        game_name=game["name"],
        query_text=None,
    )

    for patch in patches:
        patch["display_date"] = (
            format_patch_date(
                patch["source_date"]
            )
        )

        patch["display_title"] = (
            normalize_patch_title(
                game_name=patch[
                    "game_name"
                ],
                translated_title=patch[
                    "display_title"
                ],
                original_title=patch[
                    "original_title"
                ],
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="game_detail.html",
        context={
            "page_title": game["name"],
            "game": game,
            "current_price": price_view,
            "patches": patches,
        },
    )

@router.get(
    "/patches",
    response_class=HTMLResponse,
)
def patch_list(
    request: Request,
    game: str | None = None,
    q: str | None = None,
    page: int = 1,
):
    page_size = 10

    selected_game = (
        game.strip()
        if game
        else None
    )

    search_query = (
        q.strip()
        if q
        else None
    )

    total_count = get_patch_viewer_count(
        game_name=selected_game,
        query_text=search_query,
    )

    total_pages = max(
        1,
        ceil(
            total_count
            / page_size
        ),
    )

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    offset = (
        page - 1
    ) * page_size

    patches = get_patch_viewer_list(
        limit=page_size,
        offset=offset,
        game_name=selected_game,
        query_text=search_query,
    )

    for patch in patches:
        patch["display_date"] = (
            format_patch_date(
                patch["source_date"]
            )
        )

        patch["display_title"] = (
            normalize_patch_title(
                game_name=patch[
                    "game_name"
                ],
                translated_title=patch[
                    "display_title"
                ],
                original_title=patch[
                    "original_title"
                ],
            )
        )
        patch["summary_items"] = (
            build_summary_items(
                patch["summary"]
            )
        )

    games = get_patch_viewer_games()

    def build_page_url(
        target_page: int,
    ) -> str:
        params = {
            "page": target_page,
        }

        if selected_game:
            params["game"] = (
                selected_game
            )

        if search_query:
            params["q"] = (
                search_query
            )

        return (
            "/patches?"
            + urlencode(params)
        )

    previous_url = None

    if page > 1:
        previous_url = (
            build_page_url(
                page - 1
            )
        )

    next_url = None

    if page < total_pages:
        next_url = (
            build_page_url(
                page + 1
            )
        )

    start_page = max(
        1,
        page - 2,
    )

    end_page = min(
        total_pages,
        page + 2,
    )

    page_items = [
        {
            "number": number,
            "url": build_page_url(
                number
            ),
            "current": (
                number == page
            ),
        }
        for number in range(
            start_page,
            end_page + 1,
        )
    ]

    return templates.TemplateResponse(
        request=request,
        name="patches.html",
        context={
            "page_title": (
                "Game Patch Viewer"
            ),
            "patches": patches,
            "games": games,
            "selected_game": (
                selected_game
            ),
            "search_query": (
                search_query
            ),
            "total_count": (
                total_count
            ),
            "current_page": page,
            "total_pages": (
                total_pages
            ),
            "previous_url": (
                previous_url
            ),
            "next_url": (
                next_url
            ),
            "page_items": (
                page_items
            ),
        },
    )

@router.get(
    "/patches/{patch_id}",
    response_class=HTMLResponse,
    name="patch_detail",
)
def patch_detail(
    request: Request,
    patch_id: int,
):
    patch = get_patch_viewer_detail(
        patch_id=patch_id,
    )

    if patch is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "page_title": (
                    "패치를 찾을 수 없습니다"
                ),
            },
            status_code=404,
        )

    patch["display_date"] = (
        format_patch_date(
            patch["source_date"]
        )
    )

    patch["display_title"] = (
        normalize_patch_title(
            game_name=patch[
                "game_name"
            ],
            translated_title=patch[
                "display_title"
            ],
            original_title=patch[
                "original_title"
            ],
        )
    )

    summary_items = build_summary_items(
        patch["summary"]
    )

    cleaned_display_content = (
        clean_patch_content(
            patch["display_content"]
        )
    )

    content_blocks = build_patch_blocks(
        cleaned_display_content
    )

    cleaned_original_content = (
        clean_patch_content(
            patch["original_content"]
        )
    )

    original_blocks = build_patch_blocks(
        cleaned_original_content
    )

    return templates.TemplateResponse(
        request=request,
        name="patch_detail.html",
        context={
            "page_title": patch[
                "display_title"
            ],
            "patch": patch,
            "summary_items": summary_items,
            "content_blocks": content_blocks,
            "original_blocks": original_blocks,
        },
    )

@router.post(
    "/patches/{patch_id}/process"
)
def process_patch_from_web(
    patch_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    patch = get_patch_viewer_detail(
        patch_id
    )

    if patch is None:
        return RedirectResponse(
            url="/patches",
            status_code=303,
        )

    background_tasks.add_task(
        process_patch_by_id,
        patch_id,
        force,
    )

    return RedirectResponse(
        url=(
            f"/patches/{patch_id}"
            "?processing_started=1"
        ),
        status_code=303,
    )