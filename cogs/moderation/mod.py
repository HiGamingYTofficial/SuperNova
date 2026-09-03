"""cogs/moderation/mod.py — moderation commands, grouped under /mod."""

from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


class ModGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="mod", description="Moderation commands (server-only).")

    @staticmethod
    async def _reply_error(interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, discord.Forbidden):
            message = (
                "I don't have permission to do that. Check that I have the right "
                "permission enabled, and that my role is positioned ABOVE the "
                "target member's highest role in Server Settings → Roles."
            )
        elif isinstance(error, discord.HTTPException):
            message = f"Discord rejected that action: {error}"
        else:
            message = f"Something went wrong: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from this server.")
    @app_commands.describe(member="Member to kick.", reason="Reason shown in the audit log.")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.") -> None:
        try:
            await member.kick(reason=reason)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        await interaction.response.send_message(f"Kicked {member.mention}. Reason: {reason}")

    @app_commands.command(name="ban", description="Ban a member from this server.")
    @app_commands.describe(member="Member to ban.", reason="Reason shown in the audit log.")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.") -> None:
        try:
            await member.ban(reason=reason)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        await interaction.response.send_message(f"Banned {member.mention}. Reason: {reason}")

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.describe(member="Member to time out.", minutes="Duration in minutes (max 40320 / 28 days).")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320]) -> None:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=f"Timed out by {interaction.user}")
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        await interaction.response.send_message(f"{member.mention} timed out for {minutes} minute(s).")

    @app_commands.command(name="purge", description="Delete recent messages in this channel.")
    @app_commands.describe(count="Number of messages to delete (max 100).")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 100]) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=count)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member (logged in-memory).")
    @app_commands.describe(member="Member to warn.", reason="Reason for the warning.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
        bot = interaction.client
        if not hasattr(bot, "warnings"):
            bot.warnings: dict[int, list[str]] = {}
        bot.warnings.setdefault(member.id, []).append(reason)
        count = len(bot.warnings[member.id])
        await interaction.response.send_message(f"⚠️ Warned {member.mention} (warning #{count}). Reason: {reason}")

    @app_commands.command(name="warnings", description="List a member's warnings.")
    @app_commands.describe(member="Member to check.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        bot = interaction.client
        entries = getattr(bot, "warnings", {}).get(member.id, [])
        if not entries:
            await interaction.response.send_message(f"{member.mention} has no warnings.", ephemeral=True)
            return
        listing = "\n".join(f"{i + 1}. {reason}" for i, reason in enumerate(entries))
        await interaction.response.send_message(f"Warnings for {member.mention}:\n{listing}", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID.")
    @app_commands.describe(user_id="The numeric user ID to unban.", reason="Reason shown in the audit log.")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided.") -> None:
        try:
            user = discord.Object(id=int(user_id))
        except ValueError:
            await interaction.response.send_message("That doesn't look like a valid user ID.", ephemeral=True)
            return
        try:
            await interaction.guild.unban(user, reason=reason)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        await interaction.response.send_message(f"Unbanned user ID `{user_id}`.")

    @app_commands.command(name="slowmode", description="Set slowmode delay for this channel.")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600).")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]) -> None:
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        if seconds == 0:
            await interaction.response.send_message("Slowmode disabled.")
        else:
            await interaction.response.send_message(f"Slowmode set to {seconds} second(s).")

    @app_commands.command(name="nickname", description="Change a member's nickname.")
    @app_commands.describe(member="Member to rename.", nickname="New nickname (leave blank to reset).")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.guild_only()
    async def nickname(self, interaction: discord.Interaction, member: discord.Member, nickname: str | None = None) -> None:
        try:
            await member.edit(nick=nickname)
        except (discord.Forbidden, discord.HTTPException) as error:
            await self._reply_error(interaction, error)
            return
        if nickname:
            await interaction.response.send_message(f"Renamed {member.mention} to `{nickname}`.")
        else:
            await interaction.response.send_message(f"Reset {member.mention}'s nickname.")


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(ModGroup())
