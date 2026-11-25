"""Claim, send and record one price notification."""
import asyncio
import logging

import discord

from game_data_platform.discord_price_notification_worker import (
    claim_ready_price_notifications,
    mark_price_notification_sent,
    mark_price_notification_failed,
    cancel_price_notification,
)
from game_data_platform.discord_price_notification_sender import (
    PriceDeliveryStale,
    PriceDeliveryNotEligible,
    send_price_notification,
)

logger = logging.getLogger(__name__)
DELIVERY_TIMEOUT_SECONDS = 60


async def dispatch_one_price_notification(
    client: discord.Client,
    notification_id: int | None = None,
) -> str:
    """Return empty, sent, cancelled, retry, failed or stale."""
    jobs = await asyncio.to_thread(
        claim_ready_price_notifications, limit=1, notification_id=notification_id,
    )
    if not jobs:
        return "empty"
    job = jobs[0]
    job_id = job["notification_id"]
    attempt = job["attempt_count"]
    try:
        message_id = await asyncio.wait_for(
            send_price_notification(client, job), timeout=DELIVERY_TIMEOUT_SECONDS,
        )
    except PriceDeliveryStale:
        logger.warning("Stale price notification: id=%s", job_id)
        return "stale"
    except PriceDeliveryNotEligible as exc:
        updated = await asyncio.to_thread(cancel_price_notification, job_id, attempt, str(exc))
        return "cancelled" if updated else "stale"
    except Exception as exc:
        if isinstance(exc, discord.HTTPException):
            retryable = exc.status == 429 or 500 <= exc.status < 600
            error = f"Discord HTTP {exc.status} (code={exc.code})"
        else:
            retryable = not isinstance(exc, (ValueError, TypeError))
            # Avoid persisting arbitrary exception strings (URLs, credentials).
            error = type(exc).__name__
        logger.warning("Price delivery error: id=%s error=%s retryable=%s", job_id, error, retryable)
        return await asyncio.to_thread(
            mark_price_notification_failed, job_id, attempt, error, retryable=retryable,
        )

    # Deliberately outside the send exception handler. If DB persistence fails,
    # do not incorrectly record the successfully sent message as a send failure.
    try:
        updated = await asyncio.to_thread(mark_price_notification_sent, job_id, attempt)
    except Exception:
        logger.error("Price DM sent but DB result uncertain: id=%s message_id=%s", job_id, message_id)
        raise
    if not updated:
        logger.warning("Price DM sent but ownership lost: id=%s message_id=%s", job_id, message_id)
        return "stale"
    logger.info("Price notification sent: id=%s message_id=%s", job_id, message_id)
    return "sent"
