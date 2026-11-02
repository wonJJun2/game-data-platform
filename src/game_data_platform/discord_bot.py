
import asyncio
import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from game_data_platform.storage import get_games
from game_data_platform.discord_subscription_service import (
    subscribe_game,
    unsubscribe_game,
    get_subscribed_games,
)

load_dotenv()

logger = logging.getLogger(__name__)

class GameDataBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 개발 중에는 테스트 서버에만 명령어 등록
        guild_id = int(os.environ["DISCORD_GUILD_ID"])
        guild = discord.Object(id=guild_id)

        self.tree.copy_global_to(guild=guild)

        synced = await self.tree.sync(guild=guild)

        print(f"Slash commands registered: {len(synced)}")

    async def on_ready(self):
        print(f"Discord Bot connected: {self.user}")


bot = GameDataBot()


@bot.tree.command(
    name="ping",
    description="봇 연결 상태를 확인합니다.",
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Pong! 🏓",
        ephemeral=True,
    )


@bot.tree.command(
    name="game",
    description="DB에 등록된 게임을 검색합니다.",
)
@app_commands.describe(name="검색할 게임 이름")
async def game(
    interaction: discord.Interaction,
    name: str,
):
    # DB 조회가 길어질 수 있으므로 응답을 먼저 예약
    await interaction.response.defer(
        ephemeral=True,
        thinking=True,
    )

    try:
        # 기존 동기 DB 함수를 별도 스레드에서 실행
        games = await asyncio.to_thread(get_games)
    except Exception:
        logger.exception("Game search DB error")
        await interaction.followup.send(
            "게임 데이터를 조회하는 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    keyword = name.strip().casefold()

    matches = [
        game
        for game in games
        if keyword in game["name"].casefold()
    ] if keyword else []

    if not matches:
        await interaction.followup.send(
            f"'{name}'에 해당하는 게임을 찾지 못했습니다.",
            ephemeral=True,
        )
        return

    # 정확히 일치하는 이름을 우선 표시
    matches.sort(
        key=lambda game: (
            game["name"].casefold() != keyword,
            game["name"].casefold(),
        )
    )

    lines = [
        (
            f"🎮 **{discord.utils.escape_markdown(item['name'])}**\n"
            f"Steam App ID: `{item['steam_app_id']}`"
        )
        for item in matches[:5]
    ]

    await interaction.followup.send(
        "**게임 검색 결과**\n\n" + "\n\n".join(lines),
        ephemeral=True,
    )


@bot.tree.command(
    name="subscribe",
    description="관심 게임의 패치 알림을 구독합니다.",
)
@app_commands.describe(game="구독할 게임 이름")
async def subscribe(
    interaction: discord.Interaction,
    game: str,
):
    await interaction.response.defer(
        ephemeral=True,
        thinking=True,
    )

    # 서버별 구독을 관리하므로 서버 ID가 필요
    if interaction.guild_id is None:
        await interaction.followup.send(
            "서버에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    try:
        games = await asyncio.to_thread(get_games)

        keyword = game.strip().casefold()

        if not keyword:
            await interaction.followup.send(
                "구독할 게임 이름을 입력해 주세요.",
                ephemeral=True,
            )
            return

        matches = [
            item
            for item in games
            if keyword in item["name"].casefold()
        ]

        # 이름이 정확히 일치하는 게임 우선
        exact_match = next(
            (
                item
                for item in matches
                if item["name"].casefold() == keyword
            ),
            None,
        )

        if exact_match is not None:
            selected = exact_match
        elif len(matches) == 1:
            selected = matches[0]
        elif not matches:
            await interaction.followup.send(
                "해당 게임을 찾지 못했습니다. "
                "/game 명령어로 먼저 검색해 주세요.",
                ephemeral=True,
            )
            return
        else:
            await interaction.followup.send(
                "검색된 게임이 여러 개입니다. "
                "/game으로 확인한 후 정확한 이름을 입력해 주세요.",
                ephemeral=True,
            )
            return

        created = await asyncio.to_thread(
            subscribe_game,
            interaction.guild_id,
            interaction.user.id,
            selected["game_id"],
        )

        safe_name = discord.utils.escape_mentions(
            discord.utils.escape_markdown(selected["name"])
        )

        if created:
            message = f"✅ **{safe_name}** 구독이 등록되었습니다."
        else:
            message = f"ℹ️ **{safe_name}**은(는) 이미 구독 중입니다."

        await interaction.followup.send(
            message,
            ephemeral=True,
        )

    except Exception:
        logger.exception("Discord game subscription error")

        await interaction.followup.send(
            "게임 구독 처리 중 오류가 발생했습니다.",
            ephemeral=True,
        )


@bot.tree.command(
    name="subscriptions",
    description="내가 구독한 게임 목록을 확인합니다.",
)
async def subscriptions(
    interaction: discord.Interaction,
):
    await interaction.response.defer(
        ephemeral=True,
        thinking=True,
    )

    if interaction.guild_id is None:
        await interaction.followup.send(
            "서버에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    try:
        games = await asyncio.to_thread(
            get_subscribed_games,
            interaction.guild_id,
            interaction.user.id,
        )

        if not games:
            await interaction.followup.send(
                "아직 구독한 게임이 없습니다.\n"
                "/subscribe 명령어로 게임을 구독해 보세요.",
                ephemeral=True,
            )
            return

        lines = []

        for game in games[:10]:
            safe_name = discord.utils.escape_mentions(
                discord.utils.escape_markdown(
                    game["name"][:100]
                )
            )

            lines.append(
                f"🎮 **{safe_name}**\n"
                f"Steam App ID: `{game['steam_app_id']}`"
            )

        message = (
            f"**내 구독 게임 ({len(games)}개)**\n\n"
            + "\n\n".join(lines)
        )

        if len(games) > 10:
            message += "\n\n상위 10개 게임만 표시합니다."

        await interaction.followup.send(
            message,
            ephemeral=True,
        )

    except Exception:
        logger.exception(
            "Discord subscriptions lookup error"
        )

        await interaction.followup.send(
            "구독 목록 조회 중 오류가 발생했습니다.",
            ephemeral=True,
        )


@bot.tree.command(
    name="unsubscribe",
    description="관심 게임의 패치 알림 구독을 해제합니다.",
)
@app_commands.describe(game="구독 해제할 게임 이름")
async def unsubscribe(
    interaction: discord.Interaction,
    game: str,
):
    await interaction.response.defer(
        ephemeral=True,
        thinking=True,
    )

    if interaction.guild_id is None:
        await interaction.followup.send(
            "서버에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    try:
        # 현재 사용자가 구독한 게임만 조회
        games = await asyncio.to_thread(
            get_subscribed_games,
            interaction.guild_id,
            interaction.user.id,
        )

        keyword = game.strip().casefold()

        if not keyword:
            await interaction.followup.send(
                "구독 해제할 게임 이름을 입력해 주세요.",
                ephemeral=True,
            )
            return

        matches = [
            item
            for item in games
            if keyword in item["name"].casefold()
        ]

        exact_match = next(
            (
                item
                for item in matches
                if item["name"].casefold() == keyword
            ),
            None,
        )

        if exact_match is not None:
            selected = exact_match
        elif len(matches) == 1:
            selected = matches[0]
        elif not matches:
            await interaction.followup.send(
                "해당 게임을 구독하고 있지 않습니다.",
                ephemeral=True,
            )
            return
        else:
            await interaction.followup.send(
                "일치하는 구독 게임이 여러 개입니다. "
                "정확한 게임 이름을 입력해 주세요.",
                ephemeral=True,
            )
            return

        removed = await asyncio.to_thread(
            unsubscribe_game,
            interaction.guild_id,
            interaction.user.id,
            selected["game_id"],
        )

        safe_name = discord.utils.escape_mentions(
            discord.utils.escape_markdown(
                selected["name"]
            )
        )

        if removed:
            message = (
                f"✅ **{safe_name}** 구독이 해제되었습니다."
            )
        else:
            message = (
                f"ℹ️ **{safe_name}**은(는) "
                "이미 구독이 해제된 상태입니다."
            )

        await interaction.followup.send(
            message,
            ephemeral=True,
        )

    except Exception:
        logger.exception(
            "Discord game unsubscribe error"
        )

        await interaction.followup.send(
            "게임 구독 해제 중 오류가 발생했습니다.",
            ephemeral=True,
        )


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    guild_id = os.getenv("DISCORD_GUILD_ID")

    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not configured"
        )

    if not guild_id or not guild_id.isdecimal():
        raise RuntimeError(
            "DISCORD_GUILD_ID is not configured correctly"
        )

    bot.run(token)


if __name__ == "__main__":
    main()
