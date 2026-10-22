from airflow.sdk import dag, task
import pendulum

from game_data_platform.price_collector import (
    collect_game_prices,
)


@dag(
    dag_id="price_collection",
    schedule="0 */6 * * *",
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="Asia/Seoul",
    ),
    catchup=False,
    tags=[
        "game-data-project",
        "steam",
        "price",
    ],
)
def price_collection():

    @task
    def collect_prices():
        result = collect_game_prices(
            country_code="KR",
        )

        print(
            "Price collection result:",
            result,
        )

        return result

    collect_prices()


price_collection()