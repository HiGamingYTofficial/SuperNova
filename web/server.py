"""web/server.py — aiohttp application that runs alongside the Discord
gateway connection. Exposes /health, / (dashboard), /metrics.

If DASHBOARD_USERNAME and DASHBOARD_PASSWORD are set, the dashboard
and /metrics require HTTP Basic Auth. If unset, it's fully public.
"""

from __future__ import annotations

import base64
import hmac
import os
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
MAX_LOG_ROWS_SHOWN = 75
MAX_USERS_SHOWN = 75


def _format_uptime(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


def _check_basic_auth(request: web.Request) -> bool:
    expected_user = os.getenv("DASHBOARD_USERNAME")
    expected_pass = os.getenv("DASHBOARD_PASSWORD")
    if not expected_user or not expected_pass:
        return True

    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[len("Basic "):]).decode("utf-8")
        given_user, given_pass = decoded.split(":", 1)
    except Exception:
        return False

    return hmac.compare_digest(given_user, expected_user) and hmac.compare_digest(given_pass, expected_pass)


@web.middleware
async def basic_auth_middleware(request: web.Request, handler):
    if request.path in ("/health", "/healthz"):
        return await handler(request)

    if not _check_basic_auth(request):
        return web.Response(
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="Bot Dashboard"'},
            text="Authentication required.",
        )
    return await handler(request)


async def health(request: web.Request) -> web.Response:
    bot: "FrameworkBot" = request.app["bot"]
    return web.json_response(
        {
            "status": "ok",
            "gateway_connected": bot.is_ready(),
            "uptime_seconds": round(time.time() - bot.launch_time, 1),
        }
    )


def _build_dashboard_context(bot: "FrameworkBot") -> dict:
    guild_list = []
    if bot.is_ready():
        for guild in bot.guilds:
            guild_list.append({"name": guild.name, "member_count": guild.member_count, "id": guild.id})
    guild_list.sort(key=lambda g: g["member_count"], reverse=True)

    recent_log = list(bot.command_log)[-MAX_LOG_ROWS_SHOWN:][::-1]
    formatted_log = []
    for entry in recent_log:
        args_str = ", ".join(f"{k}: {v}" for k, v in entry["args"].items()) if entry["args"] else "—"
        formatted_log.append(
            {
                "time": entry["time"].strftime("%Y-%m-%d %H:%M:%S UTC"),
                "command": entry["command"],
                "args": args_str,
                "user": entry["user"],
                "context": entry["context"],
                "guild_name": entry["guild_name"] or "—",
            }
        )

    installed_users = sorted(bot.known_installed_users.values(), key=lambda u: u["last_seen"], reverse=True)
    formatted_users = [
        {
            "username": u["username"],
            "first_seen": u["first_seen"].strftime("%Y-%m-%d %H:%M UTC"),
            "last_seen": u["last_seen"].strftime("%Y-%m-%d %H:%M UTC"),
        }
        for u in installed_users[:MAX_USERS_SHOWN]
    ]

    return {
        "bot_name": str(bot.user) if bot.user else "starting…",
        "ready": bot.is_ready(),
        "guild_count": len(bot.guilds) if bot.is_ready() else 0,
        "latency_ms": round(bot.latency * 1000, 1) if bot.is_ready() else None,
        "uptime": _format_uptime(time.time() - bot.launch_time),
        "commands_executed": bot.stats["commands_executed"],
        "loaded_extensions": bot.stats["loaded_extensions"],
        "failed_extensions": bot.stats["failed_extensions"],
        "guild_list": guild_list,
        "command_log": formatted_log,
        "command_log_total": len(bot.command_log),
        "installed_users": formatted_users,
        "installed_user_count": len(bot.known_installed_users),
        "auth_enabled": bool(os.getenv("DASHBOARD_USERNAME") and os.getenv("DASHBOARD_PASSWORD")),
    }


async def metrics(request: web.Request) -> web.Response:
    bot: "FrameworkBot" = request.app["bot"]
    context = _build_dashboard_context(bot)
    context.pop("auth_enabled", None)
    return web.json_response(context)


@aiohttp_jinja2.template("dashboard.html")
async def dashboard(request: web.Request) -> dict:
    bot: "FrameworkBot" = request.app["bot"]
    return _build_dashboard_context(bot)


def build_web_app(*, bot: "FrameworkBot", config: "BotConfig") -> web.Application:
    app = web.Application(middlewares=[basic_auth_middleware])
    app["bot"] = bot
    app["config"] = config

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)))

    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/", dashboard)
    app.router.add_static("/static/", path=Path(__file__).parent / "static", name="static")

    return app


async def run_web_app(app: web.Application, *, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return runner
