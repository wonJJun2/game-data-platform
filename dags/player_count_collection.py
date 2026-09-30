from datetime import timedelta

import pendulum

from airflow.sdk import dag, task

from game_data_platform import GAMES, collect_game


@dag(
    dag_id="player_count_collection",
    schedule="@hourly", # schedule="0 * * * *",
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

    @task(
        retries=2,
        retry_delay=timedelta(seconds=30),
    )
    def collect_one_game(game: dict):

        collect_game(game)

    collect_one_game.expand(game=GAMES)


player_count_collection()