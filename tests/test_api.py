import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import game_data_platform.api as api_module
from game_data_platform.api import app

@pytest.fixture
def fake_game():
    return {
        "game_id": 1,
        "steam_app_id": 730,
        "name": "Counter-Strike 2",
        "created_at": "2026-09-25T12:00:00+09:00",
        "genre": None,
    }

@pytest.fixture
def fake_games(fake_game):
    return [
        fake_game,
        {
            "game_id": 2,
            "steam_app_id": 570,
            "name": "Dota 2",
            "created_at": "2026-09-25T12:00:00+09:00",
            "genre": None,
        },
    ]

@pytest.fixture
def client():
    # The full app serves HTML first on the same /games paths.
    api_app = FastAPI()
    api_app.router.routes.extend(
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.endpoint.__module__ == api_module.__name__
    )
    return TestClient(api_app)

def test_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Game Data API"
    }

def test_get_games_without_database(
    client,
    monkeypatch,
    fake_games,
):
    def fake_get_games():
        return fake_games

    monkeypatch.setattr(
        api_module,
        "get_games",
        fake_get_games,
    )

    response = client.get("/games")

    assert response.status_code == 200
    assert response.json() == fake_games

def test_get_game_without_database(
    client,
    monkeypatch,
    fake_game,
):
    def fake_get_game(game_id: int):
        return fake_game

    monkeypatch.setattr(
        api_module,
        "get_game",
        fake_get_game,
    )

    response = client.get("/games/1")

    assert response.status_code == 200
    assert response.json() == fake_game

def test_get_game_not_found(client, monkeypatch):
    def fake_get_game(game_id: int):
        return None

    monkeypatch.setattr(
        api_module,
        "get_game",
        fake_get_game,
    )

    response = client.get("/games/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Game not found"
    }

@pytest.mark.parametrize(
    "path",
    ["/games/1/player-counts", "/games/1/player-counts/latest"],
)
def test_removed_player_count_routes_return_not_found(path):
    response = TestClient(app).get(path)

    assert response.status_code == 404
