"""cogs/text/styles.py — text transform commands, grouped under /text.

These are declared as user-installable: once you (as an individual)
add the app to your account via Discord's "Add App" flow, every
command in this group works in any server or DM you're in — even
servers that never invited the bot itself. That's the real mechanism
behind "use it anywhere," in place of a self-bot (which would require
automating your personal account and violates Discord's Terms of
Service).

Grouping related commands under one Group (here: /text) is also how
the framework stays well under Discord's 100-top-level-command cap
while still reaching 300+ total actions — see COMMAND_INDEX.md.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from lib.text_effects import clap_text, mock_text, reverse_text, to_bold, to_fancy, uwuify, vaporwave_text


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class TextGroup(app_commands.Group):
    """/text — styling and message utility commands. Usable from a user
    install in any server or DM, with no bot invite required."""

    def __init__(self) -> None:
        super().__init__(name="text", description="Text styling and utility commands.")

    @app_commands.command(name="bold", description="Convert text to bold unicode.")
    @app_commands.describe(text="The text to convert.")
    async def bold(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(to_bold(text))

    @app_commands.command(name="fancy", description="Convert text to a fancy cursive unicode font.")
    @app_commands.describe(text="The text to convert.")
    async def fancy(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(to_fancy(text))

    @app_commands.command(name="uwuify", description="Uwuify your text.")
    @app_commands.describe(text="The text to uwuify.")
    async def uwuify_cmd(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(uwuify(text))

    @app_commands.command(name="say", description="Make the bot repeat something you type.")
    @app_commands.describe(text="What to say.")
    async def say(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(text)

    @app_commands.command(name="reverse", description="Reverse your text.")
    @app_commands.describe(text="The text to reverse.")
    async def reverse(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(reverse_text(text))

    @app_commands.command(name="mock", description="sPoNgEbOb mOcKiNg CaSe your text.")
    @app_commands.describe(text="The text to mock.")
    async def mock(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(mock_text(text))

    @app_commands.command(name="clap", description="👏 Put 👏 clap 👏 emojis 👏 between 👏 words.")
    @app_commands.describe(text="The text to clap-ify.")
    async def clap(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(clap_text(text))

    @app_commands.command(name="vaporwave", description="Ｃｏｎｖｅｒｔ your text to full-width vaporwave style.")
    @app_commands.describe(text="The text to convert.")
    async def vaporwave(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(vaporwave_text(text))


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(TextGroup())
