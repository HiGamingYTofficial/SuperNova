"""
main.py — Core lifecycle script.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from collections import deque
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from lib.interaction_utils import resolve_command_invocation
from web.server import build_web_app, run_web_app

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("bot.main")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ".")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
COGS_ROOT = Path(os.getenv("COGS_ROOT", "cogs"))
GUILD_SYNC_ID = os.getenv("DEV_GUILD_ID")

if not DISCORD_TOKEN:
    log.critical(
        "DISCORD_TOKEN is not set. Create a .env file (see .env.example) "
        "or set the environment variable on your host before starting."
    )
    sys.exit(1)


class BotConfig:
    def __init__(self) -> None:
        self.token = DISCORD_TOKEN
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.command_prefix = COMMAND_PREFIX
        self.web_host = WEB_HOST
        self.web_port = WEB_PORT
        self.cogs_root = COGS_ROOT
        self.dev_guild_id = int(GUILD_SYNC_ID) if GUILD_SYNC_ID else None
        self.started_at = time.time()


config = BotConfig()

intents = discord.Intents.default()
intents.message_content = os.getenv("ENABLE_MESSAGE_CONTENT", "false").lower() == "true"
intents.members = os.getenv("ENABLE_MEMBERS_INTENT", "false").lower() == "true"


class FrameworkBot(commands.Bot):
    def __init__(self, *, config: BotConfig, intents: discord.Intents) -> None:
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
        )
        self.config = config
        self.launch_time: float = time.time()
        self.web_app_runner = None
        self.stats = {
            "commands_executed": 0,
            "loaded_extensions": [],
            "failed_extensions": [],
        }
        self.command_log: deque = deque(maxlen=500)
        self.known_installed_users: dict[int, dict] = {}

    async def load_all_extensions(self) -> None:
        if not self.config.cogs_root.exists():
            log.warning("Cogs root '%s' does not exist; skipping cog load.", self.config.cogs_root)
            return

        extension_paths: list[str] = []
        for path in sorted(self.config.cogs_root.rglob("*.py")):
            if path.name.startswith("_"):
                continue
            module_path = ".".join(path.with_suffix("").parts)
            extension_paths.append(module_path)

        log.info("Discovered %d candidate extension(s) under '%s'.", len(extension_paths), self.config.cogs_root)

        results = await asyncio.gather(
            *(self._load_one(ext) for ext in extension_paths),
            return_exceptions=True,
        )
        for ext, result in zip(extension_paths, results):
            if isinstance(result, Exception):
                log.error("Failed to load extension '%s': %s", ext, result)
                self.stats["failed_extensions"].append(ext)
            else:
                self.stats["loaded_extensions"].append(ext)

        log.info(
            "Extension load complete: %d loaded, %d failed.",
            len(self.stats["loaded_extensions"]),
            len(self.stats["failed_extensions"]),
        )

    async def _load_one(self, extension: str) -> None:
        try:
            await self.load_extension(extension)
            log.info("  loaded %s", extension)
        except commands.ExtensionAlreadyLoaded:
            pass
        except Exception:
            log.exception("Error loading extension %s", extension)
            raise

    async def setup_hook(self) -> None:
        await self.load_all_extensions()

        if self.config.dev_guild_id:
            guild = discord.Object(id=self.config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d command(s) to dev guild %s.", len(synced), self.config.dev_guild_id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global command(s).", len(synced))

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s). Guilds: %d", self.user, self.user.id, len(self.guilds))

    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info("Joined guild: %s (id=%s, members=%s)", guild.name, guild.id, guild.member_count)

    async def on_command_completion(self, ctx: commands.Context) -> None:
        self.stats["commands_executed"] += 1

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.application_command:
            return

        try:
            command_path, args = resolve_command_invocation(interaction)
        except Exception:
            log.exception("Failed to parse interaction data for logging")
            command_path, args = "unknown", {}

        is_guild = interaction.guild is not None
        entry = {
            "time": discord.utils.utcnow(),
            "command": command_path,
            "args": args,
            "user": str(interaction.user),
            "user_id": interaction.user.id,
            "context": "guild" if is_guild else "personal install / DM",
            "guild_name": interaction.guild.name if interaction.guild else None,
        }
        self.command_log.append(entry)
        self.stats["commands_executed"] += 1

        if not is_guild:
            existing = self.known_installed_users.get(interaction.user.id, {})
            self.known_installed_users[interaction.user.id] = {
                "username": str(interaction.user),
                "first_seen": existing.get("first_seen", entry["time"]),
                "last_seen": entry["time"],
            }


bot = FrameworkBot(config=config, intents=intents)


async def main() -> None:
    web_app = build_web_app(bot=bot, config=config)

    async with bot:
        web_runner = await run_web_app(web_app, host=config.web_host, port=config.web_port)
        bot.web_app_runner = web_runner
        log.info("Web dashboard + health check listening on %s:%s", config.web_host, config.web_port)

        try:
            await bot.start(config.token)
        finally:
            await web_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutdown requested, exiting.")
