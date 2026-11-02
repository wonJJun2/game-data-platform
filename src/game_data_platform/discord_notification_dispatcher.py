
import asyncio
import logging

import discord

from game_data_platform.discord_notification_worker import (
    claim_ready_notifications,
    mark_notification_sent,
    mark_notification_failed,
)
from game_data_platform.discord_notification_sender import (
    send_patch_dm,
)

logger = logging.getLogger(__name__)


async def dispatch_one_notification(
    client: discord.Client,
    notification_id: int | None = None,
) -> str:
    """Outbox 알림 1건을 선점하고 전송 결과를 기록한다."""

    # 1. 발송 가능한 작업 1건 선점
    notifications = await asyncio.to_thread(
        claim_ready_notifications,
        1,
        notification_id,
    )

    if not notifications:
        return "empty"

    notification = notifications[0]

    notification_id = notification["notification_id"]
    attempt_count = notification["attempt_count"]

    try:
        # 2. Discord DM 전송
        message_id = await send_patch_dm(
            client,
            notification,
        )

    except Exception as exc:
        logger.exception(
            "Discord notification delivery failed: id=%s",
            notification_id,
        )

        # Discord HTTP 오류 중 429와 5xx는 재시도
        # 403, 404 등은 영구 실패로 분류
        if isinstance(exc, discord.HTTPException):
            retryable = (
                exc.status == 429
                or 500 <= exc.status < 600
            )
        else:
            retryable = True

        # 3-A. 실패 상태 기록
        updated = await asyncio.to_thread(
            mark_notification_failed,
            notification_id,
            attempt_count,
            f"{type(exc).__name__}: {exc}",
            retryable=retryable,
        )

        if not updated:
            logger.warning(
                "Stale notification failure result: id=%s",
                notification_id,
            )
            return "stale"

        if retryable and attempt_count < 5:
            return "retry"

        return "failed"

    # 3-B. 성공 상태 기록
    updated = await asyncio.to_thread(
        mark_notification_sent,
        notification_id,
        attempt_count,
    )

    if not updated:
        logger.warning(
            "Stale notification success result: id=%s",
            notification_id,
        )
        return "stale"

    logger.info(
        "Discord notification sent: id=%s message_id=%s",
        notification_id,
        message_id,
    )

    return "sent"
