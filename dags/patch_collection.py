from datetime import timedelta

import pendulum

from airflow.sdk import dag, task

from game_data_platform.patch_pipeline import (
    run_patch_pipeline,
)


@dag(
    dag_id="patch_collection",
    schedule="30 */6 * * *",
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="Asia/Seoul",
    ),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    tags=[
        "game-data-project",
        "patch",
        "news",
    ],
)
def patch_collection():

    @task(
        retries=0,
    )
    def collect_patches():
        result = run_patch_pipeline(
            llm_process_limit=1,
        )

        print(
            "Patch collection result:",
            result,
        )

    collect_patches()


patch_collection()