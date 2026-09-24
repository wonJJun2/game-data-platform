from fastapi import FastAPI, HTTPException, Query
from typing import Literal
from game_data_platform.storage import (
    get_game,
    get_games,
    get_latest_player_count,
    get_player_counts,
)

app = FastAPI()


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

@app.get("/games/{game_id}/player-counts")
def read_player_counts(
    game_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    order: Literal["asc", "desc"] = "desc",
):
    game = get_game(game_id)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )

    return get_player_counts(
        game_id=game_id,
        limit=limit,
        order=order,
    )

@app.get("/games/{game_id}/player-counts/latest")
def read_latest_player_count(game_id: int):
    game = get_game(game_id)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )

    player_count = get_latest_player_count(game_id)

    if player_count is None:
        raise HTTPException(
            status_code=404,
            detail="Player count not found",
        )

    return player_count