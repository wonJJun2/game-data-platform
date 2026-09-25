import pytest
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
def fake_player_counts():
    return [
        {
            "player_count": 1200000,
            "collected_at": "2026-09-25T21:00:00+09:00",
        },
        {
            "player_count": 1180000,
            "collected_at": "2026-09-25T20:00:00+09:00",
        },
    ]

@pytest.fixture
def fake_latest_player_count():
    return {
        "game_id": 1,
        "player_count": 1200000,
        "collected_at": "2026-09-25T21:00:00+09:00",
    }

@pytest.fixture
def client():
    return TestClient(app)

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

def test_player_counts_invalid_limit(client):
    response = client.get(
        "/games/1/player-counts?limit=0"
    )

    assert response.status_code == 422

def test_player_counts_invalid_order(client):
    response = client.get(
        "/games/1/player-counts?order=hello"
    )

    assert response.status_code == 422

def test_get_player_counts_without_database(
    client,
    monkeypatch,
    fake_game,
    fake_player_counts,
):
    def fake_get_game(game_id: int):
        return fake_game

    def fake_get_player_counts(
        game_id: int,
        limit: int = 100,
        order: str = "desc",
    ):
        return fake_player_counts

    monkeypatch.setattr(
        api_module,
        "get_game",
        fake_get_game,
    )

    monkeypatch.setattr(
        api_module,
        "get_player_counts",
        fake_get_player_counts,
    )

    response = client.get(
        "/games/1/player-counts?limit=2&order=desc"
    )

    assert response.status_code == 200
    assert response.json() == fake_player_counts

def test_get_latest_player_count_without_database(
    client,
    monkeypatch,
    fake_game,
    fake_latest_player_count,
):
    def fake_get_game(game_id: int):
        return fake_game

    def fake_get_latest_player_count(game_id: int):
        return fake_latest_player_count

    monkeypatch.setattr(
        api_module,
        "get_game",
        fake_get_game,
    )

    monkeypatch.setattr(
        api_module,
        "get_latest_player_count",
        fake_get_latest_player_count,
    )

    response = client.get(
        "/games/1/player-counts/latest"
    )

    assert response.status_code == 200
    assert response.json() == fake_latest_player_count