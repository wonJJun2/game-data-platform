from datetime import timedelta

import pendulum

from airflow.sdk import dag, task

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

    @task(
        retries=2,
        retry_delay=timedelta(seconds=30),
    )
    def collect_prices():
        result = collect_game_prices(
            country_code="KR",
        )

        print(
            "Price collection result:",
            result,
        )

        if result["retryable_failed"] > 0:
            raise RuntimeError(
                "Retryable price collection failures: "
                f"{result['retryable_failed']}"
            )

        return result

    collect_prices()


price_collection()