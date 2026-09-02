"""
web/server.py — aiohttp application that runs alongside the Discord
gateway connection inside the same asyncio event loop.

Exposes:
  GET /health   -> plain-text/JSON liveness probe for uptime pingers
                    (UptimeRobot, Freshping, a cron curl, the platform's
                    own health checks, etc.) to keep a free-tier
                    container from idling down.
  GET /         -> human-readable status dashboard (guild count,
                    latency, loaded/failed cogs, uptime).
  GET /metrics  -> machine-readable JSON version of the same data.

This module never imports discord.py's networking internals directly —
it only reads attributes off the `bot` instance it's given, so the web
layer stays decoupled from gateway logic and can be tested or reused
independently.
"""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web
import jinja2
import aiohttp_jinja2

if TYPE_CHECKING:
    from main import BotConfig, FrameworkBot

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _format_uptime(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


async def health(request: web.Request) -> web.Response:
    """Cheap, dependency-free liveness probe. Intentionally does NOT
    require the Discord gateway to be connected, so external pingers
    get a fast 200 even during a reconnect/backoff window — the
    process being alive is what keeps the container from being
    recycled by the host."""
    bot: "FrameworkBot" = request.app["bot"]
    return web.json_response(
        {
            "status": "ok",
            "gateway_connected": bot.is_ready(),
            "uptime_seconds": round(time.time() - bot.launch_time, 1),
        }
    )


async def metrics(request: web.Request) -> web.Response:
    bot: "FrameworkBot" = request.app["bot"]
    return web.json_response(
        {
            "gateway_connected": bot.is_ready(),
            "guild_count": len(bot.guilds) if bot.is_ready() else 0,
            "latency_ms": round(bot.latency * 1000, 1) if bot.is_ready() else None,
            "uptime_seconds": round(time.time() - bot.launch_time, 1),
            "commands_executed": bot.stats["commands_executed"],
            "loaded_extensions": bot.stats["loaded_extensions"],
            "failed_extensions": bot.stats["failed_extensions"],
        }
    )


@aiohttp_jinja2.template("dashboard.html")
async def dashboard(request: web.Request) -> dict:
    bot: "FrameworkBot" = request.app["bot"]
    return {
        "bot_name": str(bot.user) if bot.user else "starting…",
        "ready": bot.is_ready(),
        "guild_count": len(bot.guilds) if bot.is_ready() else 0,
        "latency_ms": round(bot.latency * 1000, 1) if bot.is_ready() else None,
        "uptime": _format_uptime(time.time() - bot.launch_time),
        "commands_executed": bot.stats["commands_executed"],
        "loaded_extensions": bot.stats["loaded_extensions"],
        "failed_extensions": bot.stats["failed_extensions"],
    }


def build_web_app(*, bot: "FrameworkBot", config: "BotConfig") -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app["config"] = config

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)))

    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)  # common alternate path some pingers default to
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/", dashboard)
    app.router.add_static("/static/", path=Path(__file__).parent / "static", name="static")

    return app


async def run_web_app(app: web.Application, *, host: str, port: int) -> web.AppRunner:
    """Starts the aiohttp server as a background runner rather than
    calling web.run_app (which blocks forever) — this is what lets it
    live in the same event loop as the Discord client instead of a
    separate process."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return runner
