"""cogs/fun/misc.py — additional top-level fun commands, split out from
games.py to keep each file focused (see COMMAND_INDEX.md guidance on
file size as the command count grows)."""

from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said no problem — it would go to sleep too.",
    "Why did the developer go broke? Because they used up all their cache.",
    "There are only 10 types of people: those who understand binary and those who don't.",
    "Why do Java developers wear glasses? Because they don't see sharp.",
]

_WYR_PROMPTS = [
    "Would you rather have unlimited books but never be able to finish one, or finish every book you start but only ever own one?",
    "Would you rather explore space or the deep ocean?",
    "Would you rather be able to fly or be invisible?",
    "Would you rather always have to sing instead of speak, or always have to dance everywhere you walk?",
    "Would you rather live without music or without movies/TV?",
]

_RPS_CHOICES = ("rock", "paper", "scissors")
_RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


class FunMisc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="rps", description="Play rock-paper-scissors against the bot.")
    @app_commands.describe(choice="Your move.")
    @app_commands.choices(choice=[app_commands.Choice(name=c.title(), value=c) for c in _RPS_CHOICES])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]) -> None:
        bot_choice = random.choice(_RPS_CHOICES)
        player = choice.value
        if player == bot_choice:
            result = "It's a tie!"
        elif _RPS_BEATS[player] == bot_choice:
            result = "You win! 🎉"
        else:
            result = "I win! 🤖"
        await interaction.response.send_message(f"You chose **{player}**, I chose **{bot_choice}**. {result}")

    @app_commands.command(name="joke", description="Get a random joke.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def joke(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(random.choice(_JOKES))

    @app_commands.command(name="wouldyourather", description="Get a random 'would you rather' question.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def wouldyourather(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"🤔 {random.choice(_WYR_PROMPTS)}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FunMisc(bot))
