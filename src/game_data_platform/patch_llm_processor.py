import logging
import os

from game_data_platform.llm.factory import (
    create_llm_client,
)
from game_data_platform.patch_prompts import (
    SUMMARY_PROMPT_VERSION,
    SUMMARY_SYSTEM_INSTRUCTION,
    TRANSLATION_PROMPT_VERSION,
    TRANSLATION_SYSTEM_INSTRUCTION,
    build_summary_prompt,
    build_translation_prompt,
    parse_translation_response,
)
from game_data_platform.storage import (
    ensure_game_patch_processing,
    get_game_patches_for_processing,
    mark_patch_summary_failed,
    mark_patch_translation_failed,
    mark_patch_translation_skipped,
    save_patch_summary,
    save_patch_translation,
    start_patch_summary,
    start_patch_translation,
    ensure_game_patch_processing,
    get_game_patch_for_processing,
    get_game_patches_for_processing,
)
from game_data_platform.text_utils import (
    clean_patch_content,
    make_content_hash,
)


logger = logging.getLogger(__name__)

TARGET_LANGUAGE = "ko"


def normalize_language(
    language: str | None,
) -> str:
    if not language:
        return ""

    value = language.lower()

    if value.startswith("ko"):
        return "ko"

    if value.startswith("en"):
        return "en"

    return value

def needs_processing(
    patch: dict,
) -> bool:
    source_language = normalize_language(
        patch["source_language"]
    )

    cleaned_content = clean_patch_content(
        patch["content_text"]
    )

    if not cleaned_content:
        return False

    current_hash = make_content_hash(
        cleaned_content
    )

    # 원문 자체가 변경됨
    if (
        patch["source_content_hash"]
        != current_hash
    ):
        return True

    # 아직 processing row 자체가 없음
    if patch["source_content_hash"] is None:
        return True

    # -----------------------------
    # Translation 상태 확인
    # -----------------------------

    if source_language == "ko":
        if (
            patch["translation_status"]
            != "skipped"
        ):
            return True

    elif source_language == "en":
        if (
            patch["translation_status"]
            != "completed"
        ):
            return True

        if (
            patch["translation_prompt_version"]
            != TRANSLATION_PROMPT_VERSION
        ):
            return True

        if not patch["translated_title"]:
            return True

        if not patch["translated_content"]:
            return True

    else:
        # 아직 지원하지 않는 언어도
        # processor가 상태를 남길 수 있도록 처리 대상
        return True

    # -----------------------------
    # Summary 상태 확인
    # -----------------------------

    if patch["summary_status"] != "completed":
        return True

    if (
        patch["summary_prompt_version"]
        != SUMMARY_PROMPT_VERSION
    ):
        return True

    if not patch["summary"]:
        return True

    return False

def process_patch(
    patch: dict,
    client,
    force: bool = False,
) -> None:
    patch_id = patch["patch_id"]

    source_language = normalize_language(
        patch["source_language"]
    )

    cleaned_content = clean_patch_content(
        patch["content_text"]
    )

    if not cleaned_content:
        logger.warning(
            "patch_id=%s empty content",
            patch_id,
        )
        return

    content_hash = make_content_hash(
        cleaned_content
    )

    content_changed = (
        patch["source_content_hash"]
        != content_hash
    )

    initial_translation_status = (
        "skipped"
        if source_language == "ko"
        else "pending"
    )

    ensure_game_patch_processing(
        patch_id=patch_id,
        target_language=TARGET_LANGUAGE,
        source_content_hash=content_hash,
        translation_status=(
            initial_translation_status
        ),
    )

    logger.info(
        "patch_id=%s game=%s language=%s",
        patch_id,
        patch["game_name"],
        source_language,
    )

    translation_reran = False

    # ---------------------------------
    # Korean source
    # ---------------------------------

    if source_language == "ko":
        if (
            force
            or content_changed
            or patch["translation_status"]
            != "skipped"
        ):
            mark_patch_translation_skipped(
                patch_id
            )

        korean_title = patch["title"]
        korean_content = cleaned_content

    # ---------------------------------
    # English source
    # ---------------------------------

    elif source_language == "en":
        translation_needed = (
            force
            or content_changed
            or patch["translation_status"]
            != "completed"
            or patch[
                "translation_prompt_version"
            ]
            != TRANSLATION_PROMPT_VERSION
            or not patch["translated_content"]
            or not patch["translated_title"]
        )

        if translation_needed:
            logger.info(
                "patch_id=%s translating",
                patch_id,
            )

            start_patch_translation(
                patch_id
            )

            try:
                response = client.generate(
                    build_translation_prompt(
                        game_name=patch[
                            "game_name"
                        ],
                        title=patch["title"],
                        content=cleaned_content,
                    ),
                    system_instruction=(
                        TRANSLATION_SYSTEM_INSTRUCTION
                    ),
                )

                (
                    translated_title,
                    translated_content,
                ) = parse_translation_response(
                    response
                )

                save_patch_translation(
                    patch_id=patch_id,
                    translated_title=(
                        translated_title
                    ),
                    translated_content=(
                        translated_content
                    ),
                    provider=client.provider,
                    model=client.model,
                    prompt_version=(
                        TRANSLATION_PROMPT_VERSION
                    ),
                )

                korean_title = (
                    translated_title
                )

                korean_content = (
                    translated_content
                )

                translation_reran = True

            except Exception as exc:
                logger.exception(
                    "patch_id=%s "
                    "translation failed",
                    patch_id,
                )

                mark_patch_translation_failed(
                    patch_id=patch_id,
                    error=str(exc),
                )

                return

        else:
            korean_title = (
                patch["translated_title"]
            )

            korean_content = (
                patch["translated_content"]
            )

    # ---------------------------------
    # Unsupported language
    # ---------------------------------

    else:
        error = (
            "Unsupported source language: "
            f"{patch['source_language']}"
        )

        logger.error(
            "patch_id=%s %s",
            patch_id,
            error,
        )

        mark_patch_translation_failed(
            patch_id=patch_id,
            error=error,
        )

        return

    # ---------------------------------
    # Summary
    # ---------------------------------

    summary_needed = (
        force
        or content_changed
        or translation_reran
        or patch["summary_status"]
        != "completed"
        or patch[
            "summary_prompt_version"
        ]
        != SUMMARY_PROMPT_VERSION
    )

    if not summary_needed:
        logger.info(
            "patch_id=%s already processed",
            patch_id,
        )
        return

    logger.info(
        "patch_id=%s summarizing",
        patch_id,
    )

    start_patch_summary(
        patch_id
    )

    try:
        summary = client.generate(
            build_summary_prompt(
                game_name=patch["game_name"],
                title=korean_title,
                content=korean_content,
            ),
            system_instruction=(
                SUMMARY_SYSTEM_INSTRUCTION
            ),
        )

        save_patch_summary(
            patch_id=patch_id,
            summary=summary,
            provider=client.provider,
            model=client.model,
            prompt_version=(
                SUMMARY_PROMPT_VERSION
            ),
        )

        logger.info(
            "patch_id=%s completed",
            patch_id,
        )

    except Exception as exc:
        logger.exception(
            "patch_id=%s summary failed",
            patch_id,
        )

        mark_patch_summary_failed(
            patch_id=patch_id,
            error=str(exc),
        )

def process_patch_by_id(
    patch_id: int,
    force: bool = False,
) -> dict:
    patch = get_game_patch_for_processing(
        patch_id
    )

    if patch is None:
        return {
            "patch_id": patch_id,
            "status": "not_found",
        }

    if (
        not force
        and not needs_processing(patch)
    ):
        return {
            "patch_id": patch_id,
            "status": "already_completed",
        }

    client = create_llm_client()

    process_patch(
        patch=patch,
        client=client,
        force=force,
    )

    return {
        "patch_id": patch_id,
        "status": "processed",
    }

def run_patch_llm_processing(
    process_limit: int = 0,
    scan_page_size: int = 50,
) -> dict:
    client = create_llm_client()

    limit_label = (
        process_limit
        if process_limit > 0
        else "unlimited"
    )

    logger.info(
        "LLM processing started "
        "limit=%s provider=%s model=%s",
        limit_label,
        client.provider,
        client.model,
    )

    processed_count = 0
    offset = 0

    while True:
        if (
            process_limit > 0
            and processed_count >= process_limit
        ):
            break

        patches = get_game_patches_for_processing(
            limit=scan_page_size,
            offset=offset,
        )

        if not patches:
            break

        for patch in patches:
            if not needs_processing(patch):
                continue

            try:
                process_patch(
                    patch,
                    client,
                )

            except Exception:
                logger.exception(
                    "patch_id=%s "
                    "unexpected processing error",
                    patch["patch_id"],
                )

            processed_count += 1

            if (
                process_limit > 0
                and processed_count >= process_limit
            ):
                break

        offset += scan_page_size

    result = {
        "processed": processed_count,
    }

    logger.info(
        "LLM processing finished "
        "processed=%s",
        processed_count,
    )

    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    process_limit = int(
        os.getenv(
            "PATCH_LLM_PROCESS_LIMIT",
            "0",
        )
    )

    scan_page_size = int(
        os.getenv(
            "PATCH_LLM_SCAN_PAGE_SIZE",
            "50",
        )
    )

    result = run_patch_llm_processing(
        process_limit=process_limit,
        scan_page_size=scan_page_size,
    )

    print(result)


if __name__ == "__main__":
    main()