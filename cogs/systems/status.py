"""cogs/systems/status.py — example "Systems" category cog.

Systems-category commands are typically operational/administrative:
health introspection, moderation primitives, config management. This
file doubles as a live example of reading the same stats object the
web dashboard renders, so slash commands and the website stay in sync
without duplicating state.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Systems(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="status", description="Show internal bot status (mirrors the web dashboard).")
    @app_commands.default_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction) -> None:
        bot = self.bot
        loaded = len(getattr(bot, "stats", {}).get("loaded_extensions", []))
        failed = len(getattr(bot, "stats", {}).get("failed_extensions", []))
        embed = discord.Embed(title="System status", color=discord.Color.green() if failed == 0 else discord.Color.orange())
        embed.add_field(name="Guilds", value=str(len(bot.guilds)))
        embed.add_field(name="Latency", value=f"{bot.latency * 1000:.1f}ms")
        embed.add_field(name="Extensions", value=f"{loaded} loaded, {failed} failed")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reload", description="Hot-reload a specific extension by dotted path.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(extension="Dotted module path, e.g. cogs.utilities.general")
    async def reload(self, interaction: discord.Interaction, extension: str) -> None:
        try:
            await self.bot.reload_extension(extension)
        except commands.ExtensionError as exc:
            await interaction.response.send_message(f"Reload failed: `{exc}`", ephemeral=True)
            return
        await interaction.response.send_message(f"Reloaded `{extension}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Systems(bot))
