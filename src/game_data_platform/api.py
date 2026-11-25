from pathlib import Path

from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI, HTTPException
from game_data_platform.storage import (
    get_game,
    get_games,
)

from game_data_platform.web.routes import (
    router as web_router,
)

PACKAGE_DIR = Path(__file__).resolve().parent


app = FastAPI()

app.mount(
    "/static",
    StaticFiles(
        directory=PACKAGE_DIR / "static",
    ),
    name="static",
)

app.include_router(web_router)

# 기본 호출
@app.get("/")
def root():
    return {
        "message": "Game Data API"
    }


@app.get("/games")
def list_games():
    return get_games()

@app.get("/games/{game_id}")
def read_game(game_id: int):
    game = get_game(game_id)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    return game
