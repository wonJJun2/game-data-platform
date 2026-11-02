
import discord


def format_patch_notification(notification: dict) -> str:
    """Outbox 데이터로 Discord 패치 알림 메시지를 만든다."""

    game_name = discord.utils.escape_mentions(
        discord.utils.escape_markdown(
            str(notification["game_name"])[:100]
        )
    )

    patch_title = discord.utils.escape_mentions(
        discord.utils.escape_markdown(
            str(notification["patch_title"])[:200]
        )
    )

    source_url = str(
        notification.get("source_url") or ""
    ).strip().splitlines()

    source_url = source_url[0][:500] if source_url else ""

    link = (
        source_url
        if source_url.startswith(("https://", "http://"))
        else "원문 링크 없음"
    )

    return (
        "🔔 **새로운 게임 패치가 등록되었습니다!**\n\n"
        f"🎮 게임: **{game_name}**\n"
        f"📝 패치: **{patch_title}**\n"
        f"🔗 원문: {link}"
    )


async def send_patch_dm(
    client: discord.Client,
    notification: dict,
) -> int:
    """Discord 사용자에게 패치 알림 DM을 전송한다.

    성공하면 Discord 메시지 ID를 반환한다.
    전송 실패 예외는 호출한 Worker에 전달한다.
    """

    user_id = int(notification["discord_user_id"])

    if user_id <= 0:
        raise ValueError("Invalid Discord user ID")

    message_text = format_patch_notification(notification)

    user = await client.fetch_user(user_id)

    sent_message = await user.send(
        content=message_text,
        allowed_mentions=discord.AllowedMentions.none(),
    )

    return sent_message.id
