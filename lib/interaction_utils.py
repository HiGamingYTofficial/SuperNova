"""lib/interaction_utils.py — turns a raw application-command
interaction into a readable (command_path, arguments) pair."""

from __future__ import annotations

import discord

_SUB_COMMAND = 1
_SUB_COMMAND_GROUP = 2


def resolve_command_invocation(interaction: discord.Interaction) -> tuple[str, dict[str, object]]:
    data = interaction.data or {}
    name_parts = [data.get("name", "unknown")]
    options = data.get("options") or []

    while options and options[0].get("type") in (_SUB_COMMAND, _SUB_COMMAND_GROUP):
        step = options[0]
        name_parts.append(step.get("name", "?"))
        options = step.get("options") or []

    args = {opt.get("name"): opt.get("value") for opt in options if "value" in opt}
    return " ".join(name_parts), args
