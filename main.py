"""
main.py — Core lifecycle script.

Boots the discord.py client and an aiohttp web application inside the
SAME asyncio event loop. Both the Discord gateway connection and the
web server are cooperative coroutines: the loop interleaves them on
every await point, so a request to /health or the dashboard never
blocks a heartbeat to Discord, and vice versa (see ARCHITECTURE.md
for the full explanation of how this scheduling works).

Responsibilities of this file, and only this file:
  1. Read configuration from environment variables (never hardcode secrets).
  2. Construct the Bot instance with the intents the app declares it needs.
  3. Dynamically discover and load every cog under cogs/ so the command
     surface can grow to hundreds of commands without this file changing.
  4. Start the aiohttp web server (dashboard + /health) as a background
     task on the bot's own event loop, then start the Discord client.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from web.server import build_web_app, run_web_app

# Loads a local .env file if present (no-op in production, where the
# platform injects real environment variables directly).
load_dotenv()

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("bot.main")

# --------------------------------------------------------------------------
# Configuration — sourced exclusively from environment variables.
# Never read a token, secret, or webhook URL from a literal in source.
# --------------------------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
# NOTE on prefix commands: Discord only ever delivers message content to a
# bot inside servers that bot has been invited to — there is no "prefix
# command that works anywhere" analogue to a user install, because a bot
# can't read messages it was never given access to. COMMAND_PREFIX is kept
# here as an optional legacy fallback for servers the bot IS in; the
# "usable in any server or DM without an invite" behavior in this framework
# comes from the user-installable slash command groups (/text, /roleplay,
# etc. — see cogs/text/styles.py and cogs/roleplay/actions.py), not from a
# prefix.
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ".")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
COGS_ROOT = Path(os.getenv("COGS_ROOT", "cogs"))
GUILD_SYNC_ID = os.getenv("DEV_GUILD_ID")  # optional: instant slash-command sync while developing

if not DISCORD_TOKEN:
    log.critical(
        "DISCORD_TOKEN is not set. Create a .env file (see .env.example) "
        "or set the environment variable on your host before starting."
    )
    sys.exit(1)


class BotConfig:
    """Small typed holder so config is read once and passed around explicitly,
    rather than modules reaching into os.environ ad hoc."""

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

# --------------------------------------------------------------------------
# Intents — request only what the command matrix actually needs.
# Flip on message_content / members only once a cog genuinely requires it;
# both are privileged intents that must also be enabled in the Discord
# Developer Portal for the application.
# --------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = os.getenv("ENABLE_MESSAGE_CONTENT", "false").lower() == "true"
intents.members = os.getenv("ENABLE_MEMBERS_INTENT", "false").lower() == "true"


class FrameworkBot(commands.Bot):
    """Bot subclass that owns cog discovery, web-server lifecycle, and the
    shared state (uptime, stats, health) the dashboard reads from."""

    def __init__(self, *, config: BotConfig, intents: discord.Intents) -> None:
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
        )
        self.config = config
        self.launch_time: float = time.time()
        self.web_app_runner: "web.AppRunner | None" = None  # set once the web server starts
        self.stats = {
            "commands_executed": 0,
            "loaded_extensions": [],
            "failed_extensions": [],
        }

    # ----------------------------------------------------------------
    # Dynamic extension (cog) loader
    # ----------------------------------------------------------------
    async def load_all_extensions(self) -> None:
        """Recursively scan `cogs/` for python modules that define a
        `setup(bot)` coroutine (the standard discord.py extension entry
        point) and load each one. This is what lets the command surface
        scale to 300+ commands: adding a new file under cogs/<category>/
        is enough — nothing here needs to change.
        """
        if not self.config.cogs_root.exists():
            log.warning("Cogs root '%s' does not exist; skipping cog load.", self.config.cogs_root)
            return

        extension_paths: list[str] = []
        for path in sorted(self.config.cogs_root.rglob("*.py")):
            if path.name.startswith("_"):
                continue  # skip __init__.py, _helpers.py, etc.
            # Convert filesystem path -> dotted module path, e.g.
            # cogs/utilities/ping.py -> cogs.utilities.ping
            module_path = ".".join(path.with_suffix("").parts)
            extension_paths.append(module_path)

        log.info("Discovered %d candidate extension(s) under '%s'.", len(extension_paths), self.config.cogs_root)

        # Load concurrently — each load_extension call is itself synchronous
        # internally in discord.py, but wrapping the scan/gather pattern here
        # means adding hundreds of cogs stays a fixed, parallel-friendly cost
        # instead of a strictly serial one as the framework grows.
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

    # ----------------------------------------------------------------
    # Lifecycle hooks
    # ----------------------------------------------------------------
    async def setup_hook(self) -> None:
        """Called once by discord.py before connecting to the gateway.
        This is the correct place to load extensions and sync the
        application (slash) command tree — doing it here (rather than
        in on_ready, which can fire multiple times on reconnect) keeps
        startup idempotent."""
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

    async def on_command_completion(self, ctx: commands.Context) -> None:
        self.stats["commands_executed"] += 1


bot = FrameworkBot(config=config, intents=intents)


# --------------------------------------------------------------------------
# Orchestration: run the Discord client and the web server as sibling
# tasks on one event loop.
# --------------------------------------------------------------------------

async def main() -> None:
    web_app = build_web_app(bot=bot, config=config)

    async with bot:
        # Start the web server first so /health starts responding
        # (and platform uptime pingers stop seeing connection errors)
        # even during the few seconds the gateway handshake takes.
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
