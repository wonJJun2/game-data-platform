from datetime import timedelta

from sqlalchemy import func, select, text

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    DiscordPriceNotificationOutbox,
    DiscordPriceSubscription,
)


DEFAULT_MAX_DELIVERY_ATTEMPTS = 5


def claim_ready_price_notifications(
    limit: int = 1,
    notification_id: int | None = None,
    max_attempts: int = DEFAULT_MAX_DELIVERY_ATTEMPTS,
) -> list[dict]:
    """발송 가능한 Discord 가격 알림 작업을 원자적으로 선점한다.

    attempt_count:
        Worker 선점 번호. 감소시키지 않는다.

    delivery_attempt_count:
        선점 시 예약하는 발송 시도 예산. 실제 API 호출 횟수와
        일치하지 않을 수 있다. 최대 시도 횟수 판단에 사용한다.

    processing 작업은 Lease가 만료된 경우에만 재선점한다.
    구독 유효성 및 현재 선점 권한은 실제 발송 직전에 다시 확인한다.
    이 함수 자체는 Discord API를 호출하지 않는다.
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
            FROM discord_price_notification_outbox
            WHERE delivery_attempt_count >= :max_attempts
              AND (
                  (
                      status IN ('pending', 'retry')
                      AND next_attempt_at <= statement_timestamp()
                  )
                  OR (
                      status = 'processing'
                      AND lease_until IS NOT NULL
                      AND lease_until <= statement_timestamp()
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
        UPDATE discord_price_notification_outbox AS n
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
            FROM discord_price_notification_outbox
            WHERE delivery_attempt_count < :max_attempts
              AND (
                  (
                      status IN ('pending', 'retry')
                      AND next_attempt_at <= statement_timestamp()
                  )
                  OR (
                      status = 'processing'
                      AND lease_until IS NOT NULL
                      AND lease_until <= statement_timestamp()
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
            UPDATE discord_price_notification_outbox AS n
            SET
                status = 'processing',
                attempt_count = n.attempt_count + 1,
                delivery_attempt_count =
                    n.delivery_attempt_count + 1,
                lease_until = clock_timestamp() + INTERVAL '5 minutes'
            FROM picked
            WHERE n.id = picked.id
            RETURNING
                n.id AS notification_id,
                n.subscription_id,
                n.alert_generation,
                n.attempt_count,
                n.delivery_attempt_count,
                n.lease_until
        )
        SELECT
            notification_id,
            subscription_id,
            alert_generation,
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

def _validate_owner(notification_id: int, attempt_count: int) -> None:
    if type(notification_id) is not int or notification_id < 1:
        raise ValueError("notification_id must be a positive integer")
    if type(attempt_count) is not int or attempt_count < 1:
        raise ValueError("attempt_count must be a positive integer")


def _lock_owned_job(session, notification_id, attempt_count):
    job = session.scalar(
        select(DiscordPriceNotificationOutbox)
        .where(
            DiscordPriceNotificationOutbox.id == notification_id,
            DiscordPriceNotificationOutbox.status == "processing",
            DiscordPriceNotificationOutbox.attempt_count == attempt_count,
        )
        .with_for_update()
    )
    if job is None:
        return None, None
    # Read the real database clock AFTER obtaining the row lock.
    now = session.scalar(select(func.clock_timestamp()))
    if job.lease_until is None or job.lease_until <= now:
        return None, None
    return job, now


def mark_price_notification_sent(notification_id: int, attempt_count: int) -> bool:
    """Record successful external delivery; update only the current generation."""
    _validate_owner(notification_id, attempt_count)
    with SessionLocal.begin() as session:
        subscription_id = session.scalar(
            select(DiscordPriceNotificationOutbox.subscription_id).where(
                DiscordPriceNotificationOutbox.id == notification_id
            )
        )
        if subscription_id is None:
            return False
        # Subscription before outbox: consistent with subscription deletion
        # (CASCADE) and the price evaluation path.
        subscription = session.scalar(
            select(DiscordPriceSubscription)
            .where(DiscordPriceSubscription.id == subscription_id)
            .with_for_update()
        )
        if subscription is None:
            return False
        job, now = _lock_owned_job(session, notification_id, attempt_count)
        if job is None or job.subscription_id != subscription_id:
            return False
        job.status = "sent"
        job.sent_at = now
        job.lease_until = None
        job.last_error = None
        # An old generation may have been sent before the subscription changed.
        # Record that delivery without mutating the new generation.
        if (
            subscription.is_active
            and not subscription.is_armed
            and subscription.alert_generation == job.alert_generation
            and subscription.target_price == job.target_price
            and subscription.country_code == "KR"
            and job.currency == "KRW"
        ):
            subscription.last_notified_at = now
        session.flush()
    return True


def cancel_price_notification(notification_id: int, attempt_count: int, reason: str) -> bool:
    _validate_owner(notification_id, attempt_count)
    with SessionLocal.begin() as session:
        job, _ = _lock_owned_job(session, notification_id, attempt_count)
        if job is None:
            return False
        job.status = "cancelled"
        job.lease_until = None
        job.last_error = str(reason)[:2000]
        job.sent_at = None
    return True


def mark_price_notification_failed(
    notification_id: int,
    attempt_count: int,
    error: str,
    retryable: bool = True,
    max_attempts: int = DEFAULT_MAX_DELIVERY_ATTEMPTS,
) -> str:
    """Return retry, failed, or stale, using the locked row's actual budget."""
    _validate_owner(notification_id, attempt_count)
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    with SessionLocal.begin() as session:
        job, now = _lock_owned_job(session, notification_id, attempt_count)
        if job is None:
            return "stale"
        should_retry = retryable and 1 <= job.delivery_attempt_count < max_attempts
        status = "retry" if should_retry else "failed"
        delay_seconds = min(60 * (2 ** min(max(job.delivery_attempt_count - 1, 0), 6)), 3600)
        job.status = status
        job.next_attempt_at = now + timedelta(seconds=delay_seconds) if should_retry else now
        job.lease_until = None
        job.last_error = str(error)[:2000]
        job.sent_at = None
    return status
