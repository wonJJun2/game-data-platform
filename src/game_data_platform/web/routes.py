from math import ceil
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    RedirectResponse,
)
from game_data_platform.storage import (
    get_game,
    get_games,
    get_latest_player_count,
    get_player_counts,
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
from game_data_platform.patch_llm_processor import (
    process_patch_by_id,
)

KST = ZoneInfo("Asia/Seoul")

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
):
    games = get_games()

    for game in games:
        latest_player_count = (
            get_latest_player_count(
                game["game_id"]
            )
        )

        game["latest_player_count"] = (
            latest_player_count
        )

    return templates.TemplateResponse(
        request=request,
        name="games.html",
        context={
            "page_title": (
                "Game Data Viewer"
            ),
            "games": games,
            "total_count": len(games),
        },
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

    latest_player_count = (
        get_latest_player_count(
            game_id=game_id,
        )
    )

    player_counts = get_player_counts(
        game_id=game_id,
        limit=168,
        order="desc",
    )

    # 최신 168건을 가져온 뒤
    # 화면에서는 시간순으로 사용한다.
    player_counts.reverse()

    for item in player_counts:
        collected_at_kst = (
            item["collected_at"]
            .astimezone(KST)
        )

        item["display_collected_at"] = (
            collected_at_kst.strftime(
                "%m.%d %H:%M"
            )
        )

        item["chart_date"] = (
            collected_at_kst.strftime(
                "%Y-%m-%d"
            )
        )

    player_chart_data = {
        "labels": [
            item["display_collected_at"]
            for item in player_counts
        ],
        "dates": [
            item["chart_date"]
            for item in player_counts
        ],
        "values": [
            item["player_count"]
            for item in player_counts
        ],
    }

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

    patch_markers = [
        {
            "date": (
                patch["source_date"].strftime(
                    "%Y-%m-%d"
                )
                if patch["source_date"]
                else None
            ),
            "title": patch["display_title"],
            "patch_id": patch["patch_id"],
        }
        for patch in patches
        if patch["source_date"]
    ]

    return templates.TemplateResponse(
        request=request,
        name="game_detail.html",
        context={
            "page_title": game["name"],
            "game": game,
            "latest_player_count": (
                latest_player_count
            ),
            "player_counts": (
                player_counts
            ),
            "player_chart_data": (
                player_chart_data
            ),
            "patches": patches,
            "patch_markers": (
                patch_markers
            ),
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