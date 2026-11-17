from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    GamePatch,
    GamePatchProcessing,
    DiscordPatchGameSubscription,
    DiscordPatchNotificationOutbox,
)
from game_data_platform.storage import (
    get_game_patch_for_processing,
)
from game_data_platform.patch_llm_processor import (
    normalize_language,
)
from game_data_platform.text_utils import (
    clean_patch_content,
    make_content_hash,
)

def get_ready_korean_content(
    patch: dict,
) -> str | None:
    """알림 전송이 가능한 한국어 전체 본문을 반환한다.

    준비되지 않은 패치는 None을 반환한다.
    """

    # 1. 원문 정리
    cleaned_content = clean_patch_content(
        patch.get("content_text") or ""
    )

    if not cleaned_content:
        return None

    # 2. 현재 원문과 처리된 원문의 해시 비교
    current_hash = make_content_hash(
        cleaned_content
    )

    if patch.get("source_content_hash") != current_hash:
        return None

    # 3. 원문 언어 및 번역 상태 확인
    source_language = normalize_language(
        patch.get("source_language")
    )

    translation_status = patch.get(
        "translation_status"
    )

    # 한국어 원문: 정리된 원문 사용
    if source_language == "ko":
        if translation_status == "skipped":
            return cleaned_content

        return None

    # 영어 원문: 번역 완료 본문 사용
    if source_language == "en":
        translated_content = patch.get(
            "translated_content"
        )

        if (
            translation_status == "completed"
            and isinstance(translated_content, str)
            and translated_content.strip()
        ):
            return translated_content

        return None

    # 그 외 언어는 현재 지원하지 않음
    return None



def create_patch_notification_outbox(
    patch_id: int,
) -> int:
    """한국어 본문이 준비된 패치의 서버별 Outbox 생성.

    현재 DB 상태를 INSERT 시점에 재검증한다.
    """

    # 1. 패치와 번역 데이터 조회
    patch = get_game_patch_for_processing(patch_id)

    if patch is None:
        return 0

    # 2. 한국어 전체 본문 준비 확인
    korean_content = get_ready_korean_content(patch)

    if korean_content is None:
        return 0

    # 3. 검증에 사용한 원문 해시
    cleaned_content = clean_patch_content(
        patch["content_text"]
    )
    expected_hash = make_content_hash(cleaned_content)

    source_language = normalize_language(
        patch["source_language"]
    )

    # 4. 언어별 번역 상태 조건
    if source_language == "ko":
        translation_condition = (
            GamePatchProcessing.translation_status == "skipped"
        )

    elif source_language == "en":
        translation_condition = and_(
            GamePatchProcessing.translation_status == "completed",
            GamePatchProcessing.translated_content
            == korean_content,
        )

    else:
        return 0

    # 5. INSERT 시점의 DB 상태 재검증
    subscribers = (
        select(
            GamePatch.id,
            DiscordPatchGameSubscription.guild_id,
        )
        .select_from(GamePatch)
        .join(
            GamePatchProcessing,
            and_(
                GamePatchProcessing.patch_id == GamePatch.id,
                GamePatchProcessing.target_language == "ko",
            ),
        )
        .join(
            DiscordPatchGameSubscription,
            DiscordPatchGameSubscription.game_id
            == GamePatch.game_id,
        )
        .where(
            GamePatch.id == patch_id,

            # 조회 당시 원문과 현재 원문이 동일해야 함
            GamePatch.content_text == patch["content_text"],
            GamePatch.source_language == patch["source_language"],

            # 번역 처리에 사용한 원문 해시 일치
            GamePatchProcessing.source_content_hash
            == expected_hash,

            # 현재 DB의 번역 상태 재검증
            translation_condition,

            # 구독 시작 기준 확인
            DiscordPatchGameSubscription.start_after_patch_id
            .is_not(None),
            GamePatch.id
            > DiscordPatchGameSubscription.start_after_patch_id,
        )
    )

    # 6. 중복 방지 INSERT
    statement = (
        insert(DiscordPatchNotificationOutbox)
        .from_select(
            ["patch_id", "guild_id"],
            subscribers,
        )
        .on_conflict_do_nothing(
            constraint=(
                "uq_discord_patch_notification_outbox_patch_guild"
            )
        )
        .returning(DiscordPatchNotificationOutbox.id)
    )

    with SessionLocal.begin() as session:
        inserted_ids = session.execute(
            statement
        ).scalars().all()

    return len(inserted_ids)


def get_patch_notification_candidate_ids(
    *,
    after_patch_id: int = 0,
    limit: int = 100,
) -> list[int]:
    """Outbox 생성이 필요한 패치 ID를 조회한다.

    구독 서버 중 Outbox가 아직 없는 서버가
    하나 이상 존재하는 패치만 반환한다.

    번역 준비 여부는 조회 후 별도로 검증한다.
    """

    if after_patch_id < 0:
        raise ValueError(
            "after_patch_id must be >= 0"
        )

    if limit < 1:
        raise ValueError(
            "limit must be >= 1"
        )

    # 해당 패치와 서버에 기존 Outbox가 있는지
    existing_outbox = (
        select(DiscordPatchNotificationOutbox.id)
        .where(
            DiscordPatchNotificationOutbox.patch_id
            == GamePatch.id,
            DiscordPatchNotificationOutbox.guild_id
            == DiscordPatchGameSubscription.guild_id,
        )
        .correlate(
            GamePatch,
            DiscordPatchGameSubscription,
        )
        .exists()
    )

    # Outbox 생성이 필요한 구독 서버가 있는지
    eligible_subscription = (
        select(DiscordPatchGameSubscription.id)
        .where(
            DiscordPatchGameSubscription.game_id
            == GamePatch.game_id,
            DiscordPatchGameSubscription.start_after_patch_id
            .is_not(None),
            GamePatch.id
            > DiscordPatchGameSubscription.start_after_patch_id,
            ~existing_outbox,
        )
        .correlate(GamePatch)
        .exists()
    )

    statement = (
        select(GamePatch.id)
        .where(
            GamePatch.id > after_patch_id,
            eligible_subscription,
        )
        .order_by(GamePatch.id.asc())
        .limit(limit)
    )

    with SessionLocal() as session:
        return list(
            session.execute(statement).scalars().all()
        )


def enqueue_pending_patch_notifications(
    batch_size: int = 100,
) -> dict:
    """Outbox 생성 후보를 순회하여 알림 작업을 생성한다.

    번역 미완료 패치는 이번 실행에서 건너뛰며,
    다음 실행에서 다시 후보로 조회된다.

    Discord 메시지는 전송하지 않는다.
    """

    if batch_size < 1:
        raise ValueError(
            "batch_size must be >= 1"
        )

    cursor = 0
    scanned_count = 0
    created_count = 0
    not_created_count = 0

    while True:
        patch_ids = get_patch_notification_candidate_ids(
            after_patch_id=cursor,
            limit=batch_size,
        )

        if not patch_ids:
            break

        for patch_id in patch_ids:
            created = create_patch_notification_outbox(
                patch_id
            )

            scanned_count += 1
            created_count += created

            if created == 0:
                not_created_count += 1

        # 이번 실행에서는 다음 페이지로 이동
        cursor = patch_ids[-1]

    return {
        "scanned": scanned_count,
        "created": created_count,
        "not_created": not_created_count,
    }
