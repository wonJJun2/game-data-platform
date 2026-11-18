from urllib.parse import urlsplit

import discord

import asyncio
import io

from sqlalchemy import and_, func, select

from game_data_platform.database import SessionLocal
from game_data_platform.models import (
    Game,
    GamePatch,
    GamePatchProcessing,
    DiscordPatchChannel,
    DiscordPatchGameSubscription,
    DiscordPatchNotificationOutbox,
)
from game_data_platform.discord_patch_notification_service import (
    get_ready_korean_content,
)

# Discord 제한 2,000자보다 여유 있게 설정
INLINE_MESSAGE_LIMIT = 1800


def format_patch_channel_notification(
    notification: dict,
    korean_content: str,
) -> tuple[str, bytes | None]:
    """Discord 채널 알림 본문과 선택적 TXT 첨부 데이터를 구성한다.

    반환값:
        (message_text, attachment_bytes)

    attachment_bytes=None이면 메시지 본문으로 전송한다.
    """

    if not isinstance(korean_content, str) or not korean_content.strip():
        raise ValueError("Korean patch content is empty")

    game_name = discord.utils.escape_mentions(
        discord.utils.escape_markdown(
            str(notification.get("game_name") or "알 수 없는 게임")[:100]
        )
    )

    patch_title = discord.utils.escape_mentions(
        discord.utils.escape_markdown(
            str(notification.get("patch_title") or "제목 없음")[:200]
        )
    )

    raw_url = str(notification.get("source_url") or "")
    source_url = raw_url.strip().splitlines()
    source_url = source_url[0][:500] if source_url else ""

    try:
        parsed = urlsplit(source_url)
        valid_url = (
            parsed.scheme in ("https", "http")
            and bool(parsed.netloc)
            and not any(c.isspace() for c in source_url)
            and not any(c in source_url for c in ("<", ">", "`"))
        )
    except ValueError:
        valid_url = False

    link = source_url if valid_url else "원문 링크 없음"

    header = (
        "🔔 **새로운 게임 패치노트**\n\n"
        f"🎮 게임: **{game_name}**\n"
        f"📝 제목: **{patch_title}**\n"
        f"🔗 원문: {link}"
    )

    full_message = (
        f"{header}\n\n"
        "📜 **한국어 전체 패치노트**\n"
        f"{korean_content}"
    )

    # UTF-16 코드 단위 기준으로 길이를 보수적으로 검사
    message_units = len(
        full_message.encode("utf-16-le")
    ) // 2

    if message_units <= INLINE_MESSAGE_LIMIT:
        return full_message, None

    # 긴 내용은 자르지 않고 UTF-8 TXT로 전달
    message = (
        f"{header}\n\n"
        "📎 한국어 전체 패치노트는 "
        "첨부된 TXT 파일에서 확인할 수 있습니다."
    )

    return message, korean_content.encode("utf-8")


class PatchDeliveryNotEligible(Exception):
    """구독 해제, 채널 설정 삭제 등으로 발송 대상이 아님."""


class PatchContentNotReady(Exception):
    """최신 한국어 패치 본문이 준비되지 않음."""


def load_patch_notification_delivery(
    notification_id: int,
    attempt_count: int,
) -> dict:
    """발송 직전 최신 DB 상태를 확인하고 메시지 데이터를 조회한다."""

    statement = (
        select(
            DiscordPatchNotificationOutbox.id.label("notification_id"),
            DiscordPatchNotificationOutbox.patch_id,
            DiscordPatchNotificationOutbox.guild_id,
            DiscordPatchChannel.channel_id,
            Game.name.label("game_name"),
            GamePatch.title.label("patch_title"),
            GamePatch.source_url,
            GamePatch.content_text,
            GamePatch.source_language,
            GamePatchProcessing.source_content_hash,
            GamePatchProcessing.translation_status,
            GamePatchProcessing.translated_content,
        )
        .select_from(DiscordPatchNotificationOutbox)
        .join(
            GamePatch,
            GamePatch.id == DiscordPatchNotificationOutbox.patch_id,
        )
        .join(
            Game,
            Game.game_id == GamePatch.game_id,
        )
        .join(
            DiscordPatchChannel,
            DiscordPatchChannel.guild_id
            == DiscordPatchNotificationOutbox.guild_id,
        )
        .join(
            DiscordPatchGameSubscription,
            and_(
                DiscordPatchGameSubscription.guild_id
                == DiscordPatchNotificationOutbox.guild_id,
                DiscordPatchGameSubscription.game_id
                == GamePatch.game_id,
                DiscordPatchGameSubscription.start_after_patch_id
                .is_not(None),
                GamePatch.id
                > DiscordPatchGameSubscription.start_after_patch_id,
            ),
        )
        .outerjoin(
            GamePatchProcessing,
            and_(
                GamePatchProcessing.patch_id == GamePatch.id,
                GamePatchProcessing.target_language == "ko",
            ),
        )
        .where(
            DiscordPatchNotificationOutbox.id == notification_id,
            DiscordPatchNotificationOutbox.status == "processing",
            DiscordPatchNotificationOutbox.attempt_count == attempt_count,
            DiscordPatchNotificationOutbox.lease_until > func.now(),
        )
    )

    with SessionLocal() as session:
        row = session.execute(statement).mappings().one_or_none()

    if row is None:
        raise PatchDeliveryNotEligible(
            "Outbox lease, subscription or channel is no longer valid"
        )

    delivery = dict(row)

    korean_content = get_ready_korean_content(delivery)

    if korean_content is None:
        raise PatchContentNotReady(
            "Current Korean patch content is not ready"
        )

    delivery["korean_content"] = korean_content
    return delivery


async def send_patch_channel_notification(
    client: discord.Client,
    notification: dict,
) -> int:
    """현재 구독 채널로 한국어 전체 패치노트를 발송한다."""

    delivery = await asyncio.to_thread(
        load_patch_notification_delivery,
        int(notification["notification_id"]),
        int(notification["attempt_count"]),
    )

    channel_id = int(delivery["channel_id"])
    guild_id = int(delivery["guild_id"])

    channel = client.get_channel(channel_id)

    if channel is None:
        channel = await client.fetch_channel(channel_id)

    # 다른 서버나 메시지 전송 불가능한 채널로 발송 방지
    if (
        getattr(getattr(channel, "guild", None), "id", None)
        != guild_id
        or not callable(getattr(channel, "send", None))
    ):
        raise PatchDeliveryNotEligible(
            "Configured channel is not a sendable channel in the guild"
        )

    message_text, attachment = format_patch_channel_notification(
        delivery,
        delivery["korean_content"],
    )

    send_options = {
        "content": message_text,
        "allowed_mentions": discord.AllowedMentions.none(),
    }

    if attachment is None:
        sent_message = await channel.send(**send_options)
    else:
        # 보수적인 첨부파일 상한. 초과 시 본문을 자르지 않는다.
        if len(attachment) > 8 * 1024 * 1024:
            raise ValueError(
                "Korean patch attachment exceeds 8 MiB"
            )

        file = discord.File(
            io.BytesIO(attachment),
            filename=f"patch_{delivery['patch_id']}_ko.txt",
        )

        try:
            sent_message = await channel.send(
                **send_options,
                file=file,
            )
        finally:
            file.close()

    return sent_message.id
