"""cogs/social/marriage.py — a lighthearted marriage system, grouped
under /marry. User-installable: works in any server or DM once you've
added the app to your account (see cogs/text/styles.py for the pattern
this follows).

State (who's married to whom, pending proposals) is kept in memory on
the bot instance for this example — it resets on every restart. For
anything you want to survive a redeploy, back this with a real table
(e.g. `marriages(user_a, user_b, married_at)`) via an async DB driver;
nothing else in this file would need to change except the storage
calls in propose/accept/decline/divorce.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class MarriageGroup(app_commands.Group):
    """/marry — propose, accept, divorce, and check marriage status."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(name="marry", description="A lighthearted virtual marriage system.")
        self.bot = bot
        # user_id -> partner_id, symmetric (both directions stored)
        if not hasattr(bot, "marriages"):
            bot.marriages: dict[int, int] = {}
        # proposed_to_id -> proposer_id
        if not hasattr(bot, "pending_proposals"):
            bot.pending_proposals: dict[int, int] = {}

    @app_commands.command(name="propose", description="Propose marriage to someone.")
    @app_commands.describe(user="Who to propose to.")
    async def propose(self, interaction: discord.Interaction, user: discord.User) -> None:
        me = interaction.user
        if user.id == me.id:
            await interaction.response.send_message("You can't marry yourself!", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("Bots can't accept proposals (yet).", ephemeral=True)
            return
        if me.id in self.bot.marriages:
            await interaction.response.send_message("You're already married — use `/marry divorce` first.", ephemeral=True)
            return
        if user.id in self.bot.marriages:
            await interaction.response.send_message(f"{user.mention} is already married.", ephemeral=True)
            return
        self.bot.pending_proposals[user.id] = me.id
        await interaction.response.send_message(
            f"💍 {me.mention} has proposed to {user.mention}! "
            f"They can accept with `/marry accept` or decline with `/marry decline`."
        )

    @app_commands.command(name="accept", description="Accept a pending marriage proposal.")
    async def accept(self, interaction: discord.Interaction) -> None:
        me = interaction.user
        proposer_id = self.bot.pending_proposals.pop(me.id, None)
        if proposer_id is None:
            await interaction.response.send_message("You don't have a pending proposal.", ephemeral=True)
            return
        self.bot.marriages[me.id] = proposer_id
        self.bot.marriages[proposer_id] = me.id
        proposer_mention = f"<@{proposer_id}>"
        await interaction.response.send_message(f"💒 {me.mention} and {proposer_mention} are now married! Congratulations!")

    @app_commands.command(name="decline", description="Decline a pending marriage proposal.")
    async def decline(self, interaction: discord.Interaction) -> None:
        me = interaction.user
        proposer_id = self.bot.pending_proposals.pop(me.id, None)
        if proposer_id is None:
            await interaction.response.send_message("You don't have a pending proposal.", ephemeral=True)
            return
        await interaction.response.send_message(f"💔 {me.mention} declined the proposal.")

    @app_commands.command(name="divorce", description="Divorce your current partner.")
    async def divorce(self, interaction: discord.Interaction) -> None:
        me = interaction.user
        partner_id = self.bot.marriages.pop(me.id, None)
        if partner_id is None:
            await interaction.response.send_message("You're not married.", ephemeral=True)
            return
        self.bot.marriages.pop(partner_id, None)
        await interaction.response.send_message(f"💔 {me.mention} is now divorced.")

    @app_commands.command(name="info", description="See who someone is married to.")
    @app_commands.describe(user="Whose marriage status to check (defaults to you).")
    async def info(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        target = user or interaction.user
        partner_id = self.bot.marriages.get(target.id)
        if partner_id is None:
            await interaction.response.send_message(f"{target.mention} is not married.")
            return
        await interaction.response.send_message(f"💞 {target.mention} is married to <@{partner_id}>.")


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(MarriageGroup(bot))
