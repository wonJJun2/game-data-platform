
import os

import discord
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()


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
