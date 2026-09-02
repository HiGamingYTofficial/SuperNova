"""cogs/utilities/snipe.py — /snipe and /editsnipe.

Requires the Message Content privileged intent (ENABLE_MESSAGE_CONTENT=true
in .env, and "Message Content Intent" enabled for the app in the Discord
Developer Portal) — without it, Discord never sends the bot the text of
messages it didn't author, so there'd be nothing to snipe.

Guild-only regardless of the user-install decorators used elsewhere in
this framework: Discord only delivers message events to a bot inside
servers it has actually been invited to, so there's no user-installed
equivalent of "snipe anywhere."

State is kept in memory (a short deque per channel) and resets on
restart — this is a "recently deleted/edited" cache, not an audit log.
"""

from __future__ import annotations

from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

MAX_SNIPES_PER_CHANNEL = 5


class Snipe(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._deleted: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_SNIPES_PER_CHANNEL))
        self._edited: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_SNIPES_PER_CHANNEL))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        self._deleted[message.channel.id].append(
            {"author": message.author, "content": message.content, "deleted_at": discord.utils.utcnow()}
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.author.bot or before.guild is None or before.content == after.content:
            return
        self._edited[before.channel.id].append(
            {"author": before.author, "before": before.content, "after": after.content, "edited_at": discord.utils.utcnow()}
        )

    @app_commands.command(name="snipe", description="Show a recently deleted message in this channel.")
    @app_commands.describe(index="How far back to look (1 = most recent deleted message).")
    @app_commands.guild_only()
    async def snipe(self, interaction: discord.Interaction, index: app_commands.Range[int, 1, MAX_SNIPES_PER_CHANNEL] = 1) -> None:
        entries = self._deleted.get(interaction.channel_id)
        if not entries or index > len(entries):
            await interaction.response.send_message("Nothing to snipe here.", ephemeral=True)
            return
        entry = entries[-index]
        embed = discord.Embed(
            description=entry["content"] or "*(no text content — likely an embed, attachment, or empty message)*",
            color=discord.Color.red(),
            timestamp=entry["deleted_at"],
        )
        embed.set_author(name=str(entry["author"]), icon_url=entry["author"].display_avatar.url)
        embed.set_footer(text=f"Deleted message · {index}/{len(entries)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="editsnipe", description="Show a recently edited message in this channel.")
    @app_commands.describe(index="How far back to look (1 = most recent edit).")
    @app_commands.guild_only()
    async def editsnipe(self, interaction: discord.Interaction, index: app_commands.Range[int, 1, MAX_SNIPES_PER_CHANNEL] = 1) -> None:
        entries = self._edited.get(interaction.channel_id)
        if not entries or index > len(entries):
            await interaction.response.send_message("Nothing to snipe here.", ephemeral=True)
            return
        entry = entries[-index]
        embed = discord.Embed(color=discord.Color.orange(), timestamp=entry["edited_at"])
        embed.set_author(name=str(entry["author"]), icon_url=entry["author"].display_avatar.url)
        embed.add_field(name="Before", value=entry["before"] or "*(empty)*", inline=False)
        embed.add_field(name="After", value=entry["after"] or "*(empty)*", inline=False)
        embed.set_footer(text=f"Edited message · {index}/{len(entries)}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Snipe(bot))
