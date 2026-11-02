
import asyncio
import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from game_data_platform.storage import get_games


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
