from datetime import timedelta
import os
import pendulum

from airflow.sdk import dag, task

from game_data_platform.patch_pipeline import (
    run_patch_pipeline,
)

def check_collection_failures(result: dict) -> None:
    failures = result["collection_failures"]

    if any(count > 0 for count in failures.values()):
        raise RuntimeError(
            f"Patch collection partial failure: {failures}"
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

    @task(retries=0)
    def collect_patches():
        llm_limit = int(
            os.getenv("PATCH_LLM_PROCESS_LIMIT", "3")
        )

        if llm_limit < 1:
            raise ValueError(
                "PATCH_LLM_PROCESS_LIMIT must be >= 1"
            )

        result = run_patch_pipeline(
            llm_process_limit=llm_limit,
        )

        print("Patch collection result:", result)

        check_collection_failures(result)

    collect_patches()


patch_collection()