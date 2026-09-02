"""cogs/utilities/general.py — example of the standard cog shape.

Every cog is a plain discord.py Cog subclass plus a module-level async
`setup(bot)` function. The dynamic loader in main.py finds this file by
walking cogs/ and calls this setup() automatically — nothing needs to
be registered by hand.

Add new commands to this file, or copy this file as a template for a
new one in the same category directory (cogs/utilities/), to grow the
command matrix.
"""

from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands


class Utilities(commands.Cog):
    """Everyday utility commands: latency, info lookups, formatting helpers."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's gateway latency.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ping(self, interaction: discord.Interaction) -> None:
        start = time.perf_counter()
        await interaction.response.send_message("Pinging…")
        elapsed_ms = (time.perf_counter() - start) * 1000
        await interaction.edit_original_response(
            content=f"Pong! Gateway latency: `{self.bot.latency * 1000:.1f}ms` "
            f"· round trip: `{elapsed_ms:.1f}ms`"
        )

    @app_commands.command(name="userinfo", description="Show information about a server member.")
    @app_commands.describe(member="The member to look up (defaults to you).")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        member = member or interaction.user
        embed = discord.Embed(title=str(member), color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, "R") if member.joined_at else "unknown")
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, "R"))
        embed.add_field(name="Top role", value=member.top_role.mention, inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utilities(bot))
