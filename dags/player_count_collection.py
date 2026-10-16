from datetime import timedelta

import pendulum

from airflow.exceptions import AirflowSkipException
from airflow.sdk import dag, task

from game_data_platform import collect_game
from game_data_platform.storage import get_games


@dag(
    dag_id="player_count_collection",
    schedule="@hourly",  # schedule="0 * * * *",
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="Asia/Seoul",
    ),
    catchup=False,
    tags=["game-data-project", "steam"],
)
def player_count_collection():

    @task
    def get_collection_games() -> list[dict]:
        games = get_games()

        return [
            {
                "steam_app_id": game["steam_app_id"],
                "name": game["name"],
            }
            for game in games
        ]

    @task(
        retries=2,
        retry_delay=timedelta(seconds=30),
    )
    def collect_one_game(game: dict):
        try:
            collect_game(game)

        except ValueError as exc:
            raise AirflowSkipException(
                f"{game['name']} "
                f"({game['steam_app_id']}): "
                f"{exc}"
            ) from exc

    games = get_collection_games()

    collect_one_game.expand(
        game=games
    )


player_count_collection()