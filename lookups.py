"""cogs/utilities/lookups.py — info-lookup commands, split out from
general.py to keep files focused as the command count grows."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Lookups(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="avatar", description="Show a user's avatar at full size.")
    @app_commands.describe(user="Whose avatar to show (defaults to you).")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        user = user or interaction.user
        embed = discord.Embed(title=f"{user}'s avatar", color=discord.Color.blurple())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Show information about this server.")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=str(guild.owner) if guild.owner else "unknown")
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, "R"))
        embed.add_field(name="Boost level", value=f"Tier {guild.premium_tier} ({guild.premium_subscription_count} boosts)")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="Show information about a role.")
    @app_commands.describe(role="The role to look up.")
    @app_commands.guild_only()
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role) -> None:
        embed = discord.Embed(title=f"Role: {role.name}", color=role.color if role.color.value else discord.Color.blurple())
        embed.add_field(name="Members", value=str(len(role.members)))
        embed.add_field(name="Position", value=str(role.position))
        embed.add_field(name="Mentionable", value=str(role.mentionable))
        embed.add_field(name="Hoisted", value=str(role.hoist))
        embed.add_field(name="Created", value=discord.utils.format_dt(role.created_at, "R"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="Show information about a channel.")
    @app_commands.describe(channel="The channel to look up (defaults to this one).")
    @app_commands.guild_only()
    async def channelinfo(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel | None = None) -> None:
        channel = channel or interaction.channel
        embed = discord.Embed(title=f"#{channel.name}", color=discord.Color.blurple())
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title())
        embed.add_field(name="Category", value=channel.category.name if channel.category else "none")
        embed.add_field(name="Position", value=str(channel.position))
        embed.add_field(name="Created", value=discord.utils.format_dt(channel.created_at, "R"))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Lookups(bot))
