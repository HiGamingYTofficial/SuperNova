"""cogs/info/lookups.py — /info group: avatar, banner, userinfo, useraccountage, server, role, channel."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class InfoGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="info", description="Look up information about users, servers, roles, and channels.")

    @app_commands.command(name="avatar", description="Show a user's avatar at full size.")
    @app_commands.describe(user="Whose avatar to show (defaults to you).")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        user = user or interaction.user
        embed = discord.Embed(title=f"{user}'s avatar", color=discord.Color.blurple())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="banner", description="Show a user's profile banner, if they have one.")
    @app_commands.describe(user="Whose banner to show (defaults to you).")
    async def banner(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        target = user or interaction.user
        fetched = await interaction.client.fetch_user(target.id)
        if fetched.banner is None:
            await interaction.response.send_message(f"{target.mention} doesn't have a banner set.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{target}'s banner", color=discord.Color.blurple())
        embed.set_image(url=fetched.banner.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show information about a user.")
    @app_commands.describe(user="Who to look up (defaults to you).")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member | discord.User | None = None) -> None:
        user = user or interaction.user
        embed = discord.Embed(title=str(user), color=discord.Color.blurple())
        embed.set_thumbnail(url=user.display_avatar.url)
        if isinstance(user, discord.Member):
            if user.joined_at:
                embed.add_field(name="Joined server", value=discord.utils.format_dt(user.joined_at, "R"))
            embed.add_field(name="Top role", value=user.top_role.mention, inline=False)
        embed.add_field(name="Account created", value=discord.utils.format_dt(user.created_at, "R"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="useraccountage", description="Show how old a user's Discord account is.")
    @app_commands.describe(user="Who to check (defaults to you).")
    async def useraccountage(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        user = user or interaction.user
        age = discord.utils.utcnow() - user.created_at
        years, remainder_days = divmod(age.days, 365)
        parts = []
        if years:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        parts.append(f"{remainder_days} day{'s' if remainder_days != 1 else ''}")
        await interaction.response.send_message(
            f"{user.mention}'s account was created {discord.utils.format_dt(user.created_at, 'D')} "
            f"({' and '.join(parts)} ago)."
        )

    @app_commands.command(name="server", description="Show information about this server.")
    @app_commands.guild_only()
    async def server(self, interaction: discord.Interaction) -> None:
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

    @app_commands.command(name="role", description="Show information about a role.")
    @app_commands.describe(role="The role to look up.")
    @app_commands.guild_only()
    async def role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        embed = discord.Embed(title=f"Role: {role.name}", color=role.color if role.color.value else discord.Color.blurple())
        embed.add_field(name="Members", value=str(len(role.members)))
        embed.add_field(name="Position", value=str(role.position))
        embed.add_field(name="Mentionable", value=str(role.mentionable))
        embed.add_field(name="Hoisted", value=str(role.hoist))
        embed.add_field(name="Created", value=discord.utils.format_dt(role.created_at, "R"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channel", description="Show information about a channel.")
    @app_commands.describe(channel="The channel to look up (defaults to this one).")
    @app_commands.guild_only()
    async def channel(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel | None = None) -> None:
        channel = channel or interaction.channel
        embed = discord.Embed(title=f"#{channel.name}", color=discord.Color.blurple())
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title())
        embed.add_field(name="Category", value=channel.category.name if channel.category else "none")
        embed.add_field(name="Position", value=str(channel.position))
        embed.add_field(name="Created", value=discord.utils.format_dt(channel.created_at, "R"))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(InfoGroup())
