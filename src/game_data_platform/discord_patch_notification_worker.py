
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text, update

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    DiscordPatchNotificationOutbox,
)


DEFAULT_MAX_DELIVERY_ATTEMPTS = 5


def claim_ready_patch_notifications(
    limit: int = 1,
    notification_id: int | None = None,
    max_attempts: int = DEFAULT_MAX_DELIVERY_ATTEMPTS,
) -> list[dict]:
    """발송 가능한 Discord 패치 알림 작업을 원자적으로 선점한다.

    attempt_count:
        Worker 선점 번호. 감소시키지 않는다.

    delivery_attempt_count:
        발송 시도 예산. 최대 시도 횟수 판단에 사용한다.

    processing 작업은 Lease가 만료된 경우에만 재선점한다.
    """

    if not 1 <= limit <= 100:
        raise ValueError(
            "limit must be between 1 and 100"
        )

    if notification_id is not None and notification_id < 1:
        raise ValueError(
            "notification_id must be >= 1"
        )

    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be >= 1"
        )

    params = {
        "limit": limit,
        "notification_id": notification_id,
        "max_attempts": max_attempts,
    }

    # 1. 발송 시도 예산이 소진된 작업을 failed 처리
    #
    # pending/retry는 실행 예정 시각 이후,
    # processing은 Lease 만료 이후에 정리한다.
    exhausted_query = text("""
        WITH picked AS (
            SELECT id
            FROM discord_patch_notification_outbox
            WHERE delivery_attempt_count >= :max_attempts
              AND (
                  (
                      status IN ('pending', 'retry')
                      AND next_attempt_at <= NOW()
                  )
                  OR (
                      status = 'processing'
                      AND lease_until IS NOT NULL
                      AND lease_until <= NOW()
                  )
              )
              AND (
                    CAST(:notification_id AS BIGINT) IS NULL
                    OR id = :notification_id
                )
            ORDER BY created_at, id
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        )
        UPDATE discord_patch_notification_outbox AS n
        SET
            status = 'failed',
            lease_until = NULL,
            last_error = 'Maximum delivery attempts exceeded'
        FROM picked
        WHERE n.id = picked.id
    """)

    # 2. 발송 시도 예산이 남은 작업만 선점
    #
    # SKIP LOCKED를 통해 여러 Worker가 동일 작업을
    # 동시에 선점하지 않도록 한다.
    claim_query = text("""
        WITH picked AS (
            SELECT id
            FROM discord_patch_notification_outbox
            WHERE delivery_attempt_count < :max_attempts
              AND (
                  (
                      status IN ('pending', 'retry')
                      AND next_attempt_at <= NOW()
                  )
                  OR (
                      status = 'processing'
                      AND lease_until IS NOT NULL
                      AND lease_until <= NOW()
                  )
              )
              AND (
                    CAST(:notification_id AS BIGINT) IS NULL
                    OR id = :notification_id
                )
            ORDER BY created_at, id
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        ),
        claimed AS (
            UPDATE discord_patch_notification_outbox AS n
            SET
                status = 'processing',
                attempt_count = n.attempt_count + 1,
                delivery_attempt_count =
                    n.delivery_attempt_count + 1,
                lease_until = NOW() + INTERVAL '5 minutes'
            FROM picked
            WHERE n.id = picked.id
            RETURNING
                n.id AS notification_id,
                n.patch_id,
                n.guild_id,
                n.attempt_count,
                n.delivery_attempt_count,
                n.lease_until
        )
        SELECT
            notification_id,
            patch_id,
            guild_id,
            attempt_count,
            delivery_attempt_count,
            lease_until
        FROM claimed
        ORDER BY notification_id
    """)

    with SessionLocal.begin() as session:
        # 같은 트랜잭션에서 소진 작업 정리 및 신규 선점
        session.execute(
            exhausted_query,
            params,
        )

        rows = session.execute(
            claim_query,
            params,
        ).mappings().all()

    return [dict(row) for row in rows]


def mark_patch_notification_sent(
    notification_id: int,
    attempt_count: int,
) -> bool:
    """현재 Lease를 보유한 Worker의 발송 성공을 기록한다."""

    if notification_id < 1 or attempt_count < 1:
        raise ValueError(
            "notification_id and attempt_count must be >= 1"
        )

    statement = (
        update(DiscordPatchNotificationOutbox)
        .where(
            DiscordPatchNotificationOutbox.id == notification_id,
            DiscordPatchNotificationOutbox.status == "processing",
            DiscordPatchNotificationOutbox.attempt_count == attempt_count,
            DiscordPatchNotificationOutbox.lease_until > func.now(),
        )
        .values(
            status="sent",
            sent_at=func.now(),
            lease_until=None,
            last_error=None,
        )
        .returning(
            DiscordPatchNotificationOutbox.id
        )
    )

    with SessionLocal.begin() as session:
        updated_id = session.execute(
            statement
        ).scalar_one_or_none()

    return updated_id is not None


def mark_patch_notification_failed(
    notification_id: int,
    attempt_count: int,
    error: str,
    retryable: bool = True,
    max_attempts: int = DEFAULT_MAX_DELIVERY_ATTEMPTS,
) -> bool:
    """발송 실패를 기록하고 재시도 또는 최종 실패 처리한다.

    재시도 여부와 백오프는 delivery_attempt_count로 판단한다.

    현재 행을 SELECT FOR UPDATE로 잠근 뒤 처리하므로
    DB의 발송 시도 횟수를 일관되게 사용할 수 있다.
    """

    if notification_id < 1:
        raise ValueError(
            "notification_id must be >= 1"
        )

    if attempt_count < 1 or max_attempts < 1:
        raise ValueError(
            "attempt_count and max_attempts must be >= 1"
        )

    # 1. 현재 Worker가 소유한 유효한 작업을 잠금
    statement = (
        select(DiscordPatchNotificationOutbox)
        .where(
            DiscordPatchNotificationOutbox.id == notification_id,
            DiscordPatchNotificationOutbox.status == "processing",
            DiscordPatchNotificationOutbox.attempt_count == attempt_count,
            DiscordPatchNotificationOutbox.lease_until > func.now(),
            DiscordPatchNotificationOutbox.delivery_attempt_count >= 1,
        )
        .with_for_update()
    )

    with SessionLocal.begin() as session:
        notification = session.scalar(
            statement
        )

        # Lease 만료 또는 다른 Worker가 재선점한 경우
        if notification is None:
            return False

        # 2. DB에 저장된 실제 발송 시도 횟수 사용
        delivery_attempt_count = (
            notification.delivery_attempt_count
        )

        should_retry = (
            retryable
            and delivery_attempt_count < max_attempts
        )

        # 3. 지수 백오프
        #
        # 1회 실패: 60초
        # 2회 실패: 120초
        # 3회 실패: 240초
        # 4회 실패: 480초
        #
        # 최대 1시간
        delay_seconds = min(
            60 * (
                2 ** min(
                    delivery_attempt_count - 1,
                    6,
                )
            ),
            3600,
        )

        now = datetime.now(timezone.utc)

        next_attempt_at = (
            now + timedelta(seconds=delay_seconds)
            if should_retry
            else now
        )

        # 4. 실패 상태 기록
        notification.status = (
            "retry" if should_retry else "failed"
        )

        notification.next_attempt_at = next_attempt_at
        notification.lease_until = None
        notification.last_error = str(error)[:2000]
        notification.sent_at = None

    return True


def cancel_patch_notification(
    notification_id: int,
    attempt_count: int,
    reason: str,
) -> bool:
    """구독 해제 등으로 발송 대상이 아닌 작업을 종료한다.

    cancelled 작업은 자동 재선점 대상에서 제외된다.
    """

    if notification_id < 1 or attempt_count < 1:
        raise ValueError(
            "notification_id and attempt_count must be >= 1"
        )

    statement = (
        update(DiscordPatchNotificationOutbox)
        .where(
            DiscordPatchNotificationOutbox.id == notification_id,
            DiscordPatchNotificationOutbox.status == "processing",
            DiscordPatchNotificationOutbox.attempt_count == attempt_count,
            DiscordPatchNotificationOutbox.lease_until > func.now(),
        )
        .values(
            status="cancelled",
            lease_until=None,
            last_error=str(reason)[:2000],
            sent_at=None,
        )
        .returning(
            DiscordPatchNotificationOutbox.id
        )
    )

    with SessionLocal.begin() as session:
        updated_id = session.execute(
            statement
        ).scalar_one_or_none()

    return updated_id is not None


def defer_patch_notification(
    notification_id: int,
    attempt_count: int,
    reason: str,
    delay_minutes: int = 60,
) -> bool:
    """한국어 본문 미준비 작업을 나중에 다시 확인하도록 보류한다.

    번역 미완료는 Discord API 발송 실패가 아니므로
    delivery_attempt_count만 1 감소시켜 예산을 복구한다.

    attempt_count는 감소시키지 않아 Worker 선점 번호를 유지한다.
    """

    if notification_id < 1 or attempt_count < 1:
        raise ValueError(
            "notification_id and attempt_count must be >= 1"
        )

    if delay_minutes < 1:
        raise ValueError(
            "delay_minutes must be >= 1"
        )

    next_attempt_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=delay_minutes)
    )

    statement = (
        update(DiscordPatchNotificationOutbox)
        .where(
            DiscordPatchNotificationOutbox.id == notification_id,
            DiscordPatchNotificationOutbox.status == "processing",
            DiscordPatchNotificationOutbox.attempt_count == attempt_count,
            DiscordPatchNotificationOutbox.lease_until > func.now(),
            DiscordPatchNotificationOutbox.delivery_attempt_count >= 1,
        )
        .values(
            status="retry",
            delivery_attempt_count=(
                DiscordPatchNotificationOutbox.delivery_attempt_count - 1
            ),
            next_attempt_at=next_attempt_at,
            lease_until=None,
            last_error=str(reason)[:2000],
            sent_at=None,
        )
        .returning(
            DiscordPatchNotificationOutbox.id
        )
    )

    with SessionLocal.begin() as session:
        updated_id = session.execute(
            statement
        ).scalar_one_or_none()

    return updated_id is not None
