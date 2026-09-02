"""cogs/productivity/reminders.py — example "Productivity" category cog.

A minimal in-memory reminder command. In production, back this with a
real datastore (Postgres/SQLite via an async driver) instead of a
process-local dict, since state here does not survive a restart —
the framework's dynamic loader and web layer are storage-agnostic and
don't care what a given cog persists to.
"""

from __future__ import annotations

import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands


class Productivity(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="remindme", description="Get pinged after N minutes with a note.")
    @app_commands.describe(minutes="Delay in minutes (1-1440).", note="What to be reminded about.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def remindme(self, interaction: discord.Interaction, minutes: app_commands.Range[int, 1, 1440], note: str) -> None:
        await interaction.response.send_message(
            f"Okay {interaction.user.mention}, I'll remind you in {minutes} minute(s): \"{note}\"",
            ephemeral=True,
        )
        await asyncio.sleep(minutes * 60)
        try:
            await interaction.user.send(f"⏰ Reminder: {note}")
        except discord.Forbidden:
            channel = interaction.channel
            if channel:
                await channel.send(f"{interaction.user.mention} ⏰ Reminder: {note}")

    @app_commands.command(name="timestamp", description="Convert minutes-from-now into a Discord auto-localized timestamp.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timestamp(self, interaction: discord.Interaction, minutes_from_now: int) -> None:
        target = int(time.time()) + minutes_from_now * 60
        await interaction.response.send_message(f"<t:{target}:F> (<t:{target}:R>)")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Productivity(bot))
