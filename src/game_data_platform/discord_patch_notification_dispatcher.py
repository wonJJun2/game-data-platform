
import asyncio
import logging

import discord

from game_data_platform.discord_patch_notification_worker import (
    DEFAULT_MAX_DELIVERY_ATTEMPTS,
    claim_ready_patch_notifications,
    mark_patch_notification_sent,
    mark_patch_notification_failed,
    cancel_patch_notification,
    defer_patch_notification,
)

from game_data_platform.discord_patch_notification_sender import (
    PatchDeliveryNotEligible,
    PatchContentNotReady,
    send_patch_channel_notification,
)


logger = logging.getLogger(__name__)


async def dispatch_one_patch_notification(
    client: discord.Client,
    notification_id: int | None = None,
) -> str:
    """Discord 채널 패치 알림 1건을 처리한다.

    반환값:
        empty     처리할 작업 없음
        sent      Discord 전송 및 DB 성공 처리
        deferred  한국어 본문 미준비로 보류
        cancelled 구독 또는 채널 조건 불충족
        retry     일시적 실패 후 재시도 예약
        failed    최종 실패
        stale     Worker 선점 권한 만료
    """

    # 1. 발송 가능한 작업 선점
    notifications = await asyncio.to_thread(
        claim_ready_patch_notifications,
        limit=1,
        notification_id=notification_id,
    )

    if not notifications:
        return "empty"

    notification = notifications[0]

    job_id = notification["notification_id"]
    attempt_count = notification["attempt_count"]
    delivery_attempt_count = notification[
        "delivery_attempt_count"
    ]

    try:
        # 2. 최신 DB 상태 검증 후 Discord 전송
        message_id = await send_patch_channel_notification(
            client,
            notification,
        )

    except PatchDeliveryNotEligible as exc:
        # 3-A. 구독 해제, 채널 조건 불충족 등
        updated = await asyncio.to_thread(
            cancel_patch_notification,
            job_id,
            attempt_count,
            str(exc),
        )

        if not updated:
            logger.warning(
                "Stale cancellation: notification_id=%s",
                job_id,
            )
            return "stale"

        logger.info(
            "Patch notification cancelled: id=%s",
            job_id,
        )
        return "cancelled"

    except PatchContentNotReady as exc:
        # 3-B. 번역 미완료는 발송 시도 예산을 소모하지 않음
        updated = await asyncio.to_thread(
            defer_patch_notification,
            job_id,
            attempt_count,
            str(exc),
            delay_minutes=60,
        )

        if not updated:
            logger.warning(
                "Stale deferral: notification_id=%s",
                job_id,
            )
            return "stale"

        logger.info(
            "Patch notification deferred: id=%s",
            job_id,
        )
        return "deferred"

    except Exception as exc:
        # 3-C. Discord API 및 기타 전송 오류
        logger.exception(
            "Patch notification delivery failed: id=%s",
            job_id,
        )

        if isinstance(exc, discord.HTTPException):
            # 429, 5xx: 일시적 오류
            # 403, 404 등: 영구적 오류
            retryable = (
                exc.status == 429
                or 500 <= exc.status < 600
            )

        elif isinstance(exc, (ValueError, TypeError)):
            # 잘못된 데이터, 첨부파일 크기 초과 등
            retryable = False

        else:
            # 일시적 네트워크 오류 등
            retryable = True

        updated = await asyncio.to_thread(
            mark_patch_notification_failed,
            job_id,
            attempt_count,
            f"{type(exc).__name__}: {exc}",
            retryable=retryable,
        )

        if not updated:
            logger.warning(
                "Stale failure result: notification_id=%s",
                job_id,
            )
            return "stale"

        if (
            retryable
            and delivery_attempt_count
            < DEFAULT_MAX_DELIVERY_ATTEMPTS
        ):
            return "retry"

        return "failed"

    # 3-D. Discord 전송 성공
    updated = await asyncio.to_thread(
        mark_patch_notification_sent,
        job_id,
        attempt_count,
    )

    if not updated:
        logger.warning(
            "Stale success result: notification_id=%s "
            "message_id=%s",
            job_id,
            message_id,
        )
        return "stale"

    logger.info(
        "Patch notification sent: id=%s message_id=%s",
        job_id,
        message_id,
    )

    return "sent"
