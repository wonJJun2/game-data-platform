from math import ceil
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from game_data_platform.storage import (
    get_patch_viewer_count,
    get_patch_viewer_detail,
    get_patch_viewer_games,
    get_patch_viewer_list,
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

router = APIRouter()


PACKAGE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=PACKAGE_DIR / "templates",
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

    content_blocks = build_patch_blocks(
        patch["display_content"]
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