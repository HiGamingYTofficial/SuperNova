"""cogs/fun/games.py — example "Fun" category cog."""

from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="coinflip", description="Flip a coin.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def coinflip(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"🪙 {random.choice(['Heads', 'Tails'])}!")

    @app_commands.command(name="roll", description="Roll an N-sided die.")
    @app_commands.describe(sides="Number of sides (2-1000).")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def roll(self, interaction: discord.Interaction, sides: app_commands.Range[int, 2, 1000] = 6) -> None:
        await interaction.response.send_message(f"🎲 You rolled a **{random.randint(1, sides)}** (d{sides}).")

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="Your yes/no question.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def eight_ball(self, interaction: discord.Interaction, question: str) -> None:
        answers = [
            "It is certain.", "Without a doubt.", "You may rely on it.", "Ask again later.",
            "Cannot predict now.", "Don't count on it.", "My reply is no.", "Very doubtful.",
        ]
        await interaction.response.send_message(f"🎱 **{question}**\n> {random.choice(answers)}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
