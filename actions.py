"""cogs/roleplay/actions.py — anime-style roleplay action commands,
grouped under /roleplay. User-installable like /text (see styles.py).

Pulls GIFs from nekos.best, a free public API that needs no API key —
appropriate for a self-contained example. Swap in any GIF provider you
prefer; nothing else in the framework depends on this choice.

Commands are generated from the ACTIONS table below rather than
hand-written one by one — to add another action, add one line to the
table, nothing else changes. This is the same "add data, not code"
pattern the dynamic cog loader uses at the file level, applied here at
the command level.
"""

from __future__ import annotations

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

NEKOS_BEST_BASE = "https://nekos.best/api/v2"

# (nekos.best endpoint name, verb shown in the message, slash command description)
ACTIONS: list[tuple[str, str, str]] = [
    ("hug", "hugs", "Hug someone."),
    ("pat", "pats", "Pat someone."),
    ("slap", "slaps", "Slap someone (playfully)."),
    ("poke", "pokes", "Poke someone."),
    ("cuddle", "cuddles", "Cuddle someone."),
    ("highfive", "high-fives", "High-five someone."),
    ("kiss", "kisses", "Kiss someone."),
    ("tickle", "tickles", "Tickle someone."),
    ("bite", "bites", "Bite someone (playfully)."),
    ("punch", "punches", "Punch someone (playfully)."),
    ("handhold", "holds hands with", "Hold hands with someone."),
    ("feed", "feeds", "Feed someone."),
    ("wave", "waves at", "Wave at someone."),
    ("dance", "dances with", "Dance with someone."),
    ("wink", "winks at", "Wink at someone."),
    ("blush", "blushes at", "Blush at someone."),
    ("cry", "cries on", "Cry on someone's shoulder."),
    ("smile", "smiles at", "Smile at someone."),
    ("yeet", "yeets", "Yeet someone (playfully)."),
    ("pout", "pouts at", "Pout at someone."),
]


async def _fetch_action_gif(action: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{NEKOS_BEST_BASE}/{action}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data["results"][0]["url"]
    except Exception:
        return None


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class RoleplayGroup(app_commands.Group):
    """/roleplay — anime-style action GIFs you can send to anyone."""

    def __init__(self) -> None:
        super().__init__(name="roleplay", description="Anime-style roleplay action commands.")
        for action, verb, description in ACTIONS:
            self.add_command(self._build_command(action, verb, description))

    def _build_command(self, action: str, verb: str, description: str) -> app_commands.Command:
        async def callback(interaction: discord.Interaction, user: discord.User | None = None) -> None:
            await self._send(interaction, action, verb, user)

        callback.__name__ = action
        # app_commands.describe is safe to apply to a plain closure (it just
        # tags the function with the descriptions app_commands.Command reads
        # at construction time) — used here instead of docstring parsing
        # since these callbacks are built programmatically rather than
        # declared at class-definition time.
        callback = app_commands.describe(user="Who to target (optional).")(callback)
        return app_commands.Command(name=action, description=description, callback=callback)

    async def _send(self, interaction: discord.Interaction, action: str, verb: str, user: discord.User | None) -> None:
        await interaction.response.defer()
        gif_url = await _fetch_action_gif(action)
        actor = interaction.user.mention
        text = f"{actor} {verb} {user.mention}!" if user else f"{actor} {verb}!"
        embed = discord.Embed(description=text, color=discord.Color.pink())
        if gif_url:
            embed.set_image(url=gif_url)
        else:
            embed.description += "\n*(gif service unavailable right now)*"
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(RoleplayGroup())
