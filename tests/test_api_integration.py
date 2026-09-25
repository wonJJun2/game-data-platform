import pytest
from fastapi.testclient import TestClient

from game_data_platform.api import app


@pytest.mark.integration
def test_get_games_from_database():
    client = TestClient(app)

    response = client.get("/games")

    assert response.status_code == 200
    assert isinstance(response.json(), list)