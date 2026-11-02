from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, text, update

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    Game,
    GamePatch,
    PatchNotificationOutbox,
)


def list_ready_notifications(
    limit: int = 10,
) -> list[dict]:
    """발송 가능한 Outbox 작업을 조회한다.

    pending: 아직 발송하지 않은 작업
    retry: 재시도 예정 시각이 지난 작업

    이 함수는 조회만 수행하며 작업을 선점하지 않는다.
    """

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    statement = (
        select(
            PatchNotificationOutbox.id.label(
                "notification_id"
            ),
            PatchNotificationOutbox.patch_id,
            PatchNotificationOutbox.guild_id,
            PatchNotificationOutbox.discord_user_id,
            PatchNotificationOutbox.attempt_count,
            Game.name.label("game_name"),
            GamePatch.title.label("patch_title"),
            GamePatch.source_url,
        )
        .select_from(PatchNotificationOutbox)
        .join(
            GamePatch,
            PatchNotificationOutbox.patch_id
            == GamePatch.id,
        )
        .join(
            Game,
            GamePatch.game_id == Game.game_id,
        )
        .where(
            or_(
                PatchNotificationOutbox.status
                == "pending",
                and_(
                    PatchNotificationOutbox.status
                    == "retry",
                    PatchNotificationOutbox.next_attempt_at
                    <= func.now(),
                ),
            )
        )
        .order_by(
            PatchNotificationOutbox.created_at,
            PatchNotificationOutbox.id,
        )
        .limit(limit)
    )

    with SessionLocal() as session:
        rows = session.execute(
            statement
        ).mappings().all()

        return [dict(row) for row in rows]


def claim_ready_notifications(
    limit: int = 10,
    notification_id: int | None = None,
) -> list[dict]:
    """발송 가능한 알림 작업을 원자적으로 선점한다."""

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    query = text("""
        WITH picked AS (
            SELECT id
            FROM patch_notification_outbox
            WHERE (
                status = 'pending'
                OR (
                    status IN ('retry', 'processing')
                    AND next_attempt_at <= NOW()
                )
            )
            AND id = COALESCE(:notification_id, id)
            ORDER BY created_at, id
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        ),
        claimed AS (
            UPDATE patch_notification_outbox AS n
            SET
                status = 'processing',
                attempt_count = n.attempt_count + 1,
                next_attempt_at = NOW() + INTERVAL '5 minutes'
            FROM picked
            WHERE n.id = picked.id
            RETURNING
                n.id AS notification_id,
                n.patch_id,
                n.guild_id,
                n.discord_user_id,
                n.attempt_count
        )
        SELECT
            c.notification_id,
            c.patch_id,
            c.guild_id,
            c.discord_user_id,
            c.attempt_count,
            g.name AS game_name,
            gp.title AS patch_title,
            gp.source_url
        FROM claimed AS c
        JOIN game_patches AS gp
            ON gp.id = c.patch_id
        JOIN games AS g
            ON g.game_id = gp.game_id
        ORDER BY c.notification_id
    """)

    with SessionLocal.begin() as session:
        rows = session.execute(
            query,
            {
                "limit": limit,
                "notification_id": notification_id,
            },
        ).mappings().all()

        return [dict(row) for row in rows]


def mark_notification_sent(
    notification_id: int,
    attempt_count: int,
) -> bool:
    """현재 선점한 Worker가 알림을 성공 처리한다."""

    statement = (
        update(PatchNotificationOutbox)
        .where(
            PatchNotificationOutbox.id == notification_id,
            PatchNotificationOutbox.status == "processing",
            PatchNotificationOutbox.attempt_count == attempt_count,
        )
        .values(
            status="sent",
            sent_at=func.now(),
            next_attempt_at=None,
            last_error=None,
        )
        .returning(PatchNotificationOutbox.id)
    )

    with SessionLocal.begin() as session:
        updated_id = session.execute(
            statement
        ).scalar_one_or_none()

    return updated_id is not None


def mark_notification_failed(
    notification_id: int,
    attempt_count: int,
    error: str,
    retryable: bool = True,
    max_attempts: int = 5,
) -> bool:
    """전송 실패를 기록하고 재시도 또는 최종 실패 처리한다."""

    if attempt_count < 1 or max_attempts < 1:
        raise ValueError(
            "attempt_count and max_attempts must be >= 1"
        )

    should_retry = (
        retryable
        and attempt_count < max_attempts
    )

    # 지수 백오프: 60초, 120초, 240초, 480초 ...
    # 최대 대기 시간은 1시간
    delay_seconds = min(
        60 * (2 ** min(attempt_count - 1, 6)),
        3600,
    )

    next_attempt_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=delay_seconds)
        if should_retry
        else None
    )

    statement = (
        update(PatchNotificationOutbox)
        .where(
            PatchNotificationOutbox.id == notification_id,
            PatchNotificationOutbox.status == "processing",
            PatchNotificationOutbox.attempt_count == attempt_count,
        )
        .values(
            status="retry" if should_retry else "failed",
            next_attempt_at=next_attempt_at,
            last_error=str(error)[:2000],
            sent_at=None,
        )
        .returning(PatchNotificationOutbox.id)
    )

    with SessionLocal.begin() as session:
        updated_id = session.execute(
            statement
        ).scalar_one_or_none()

    return updated_id is not None
