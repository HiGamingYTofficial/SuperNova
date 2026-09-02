# Command Index — 300+ Command Matrix

This is the planning document for the full command surface. Each row is
one command; each category maps to one directory under `cogs/`. Only a
handful of commands per category are implemented as working examples in
this repository (marked **●**) — the rest are the planned slots that
the dynamic loader will pick up automatically once you add files for
them under the matching `cogs/<category>/` directory. Nothing about
`main.py` needs to change as you fill these in.

## User-installable vs. server-only

Discord commands can be **user-installed** (added to your personal
account, then usable in any server or DM you're in — no invite needed
for that server) or restricted to **guild-only** (only works in
servers the bot has actually been invited to, with permissions
granted there). This is set per command/group via the
`@app_commands.allowed_installs` / `@app_commands.allowed_contexts`
decorators — see `cogs/text/styles.py` for the pattern.

- **User-installable** (works anywhere, once you add the app to your
  account): `/text` (8 subcommands), `/roleplay` (20 subcommands),
  `/marry` (5 subcommands), `/fun`-style top-levels (`/coinflip`,
  `/roll`, `/8ball`, `/rps`, `/joke`, `/wouldyourather`), `/remindme`,
  `/timestamp`, `/ping`, `/avatar` — nothing here needs server-side data.
- **Guild-only** (needs the bot invited + permissions in that server):
  `/mod` (9 subcommands: kick/ban/timeout/purge/warn/warnings/unban/
  slowmode/nickname), `/userinfo`, `/serverinfo`, `/roleinfo`,
  `/channelinfo`, `/status`, `/reload`, `/snipe`, `/editsnipe` — these
  read or act on server-specific state (or, for snipe, server message
  events) Discord only exposes to an invited bot.

Keep this split in mind as you add new commands: if a command reads
guild-specific data (`interaction.guild`, member lists, channel
permissions) it has to stay guild-only regardless of the decorator,
since Discord simply won't populate that data outside a server
context.

| Category | Directory | Target count | Implemented here |
|---|---|---|---|
| Utilities | `cogs/utilities/` | ~80 | `/ping`, `/remindme`-adjacent lookups, `/avatar`, `/serverinfo`, `/roleinfo`, `/channelinfo`, `/userinfo`, `/snipe`, `/editsnipe` |
| Systems | `cogs/systems/` | ~70 | `/status`, `/reload` — guild-only |
| Productivity | `cogs/productivity/` | ~80 | `/remindme`, `/timestamp` — anywhere |
| Fun | `cogs/fun/` | ~70 | `/coinflip`, `/roll`, `/8ball`, `/rps`, `/joke`, `/wouldyourather` — anywhere |
| Text | `cogs/text/` | grouped | `/text` group — `bold, fancy, uwuify, say, reverse, mock, clap, vaporwave` (8 subcommands, all anywhere) |
| Roleplay | `cogs/roleplay/` | grouped | `/roleplay` group — 20 action subcommands (hug, pat, slap, poke, cuddle, highfive, kiss, tickle, bite, punch, handhold, feed, wave, dance, wink, blush, cry, smile, yeet, pout), all anywhere |
| Social | `cogs/social/` | grouped | `/marry` group — `propose, accept, decline, divorce, info`, all anywhere |
| Moderation | `cogs/moderation/` | grouped | `/mod` group — `kick, ban, timeout, purge, warn, warnings, unban, slowmode, nickname` — guild-only |

Grouping (`/text bold`, `/text fancy`, …) is also how the matrix stays
far under Discord's 100-top-level-command cap while still reaching
300+ total actions: one top-level group can hold up to 25 subcommands
(or 25 subgroups × 25 subcommands each), so 10–15 groups comfortably
cover a 300+ command surface.

## Utilities (`cogs/utilities/`)
General-purpose lookups and quality-of-life commands.
- ● `/ping` — gateway + round-trip latency
- ● `/userinfo` — member profile lookup
- `/serverinfo`, `/roleinfo`, `/channelinfo`, `/avatar`, `/banner`
- `/translate`, `/define`, `/weather`, `/timezone`, `/shorten-url`
- `/qrcode`, `/color-preview`, `/base64`, `/hash`, `/unicode-lookup`
- … continue splitting into one file per few related commands, e.g.
  `cogs/utilities/lookups.py`, `cogs/utilities/converters.py`,
  `cogs/utilities/formatting.py`.

## Systems (`cogs/systems/`)
Operational, moderation, and configuration commands — should carry
`@app_commands.default_permissions(...)` guards.
- ● `/status` — internal health snapshot (mirrors the web dashboard)
- ● `/reload` — hot-reload a single extension
- `/kick`, `/ban`, `/timeout`, `/warn`, `/purge`, `/slowmode`
- `/config get`, `/config set`, `/config list`
- `/autorole`, `/welcome-message`, `/logging-channel`
- `/backup-roles`, `/audit-log-export`
- Suggested split: `cogs/systems/moderation.py`, `cogs/systems/config.py`,
  `cogs/systems/audit.py`.

## Productivity (`cogs/productivity/`)
Personal and team-utility tooling.
- ● `/remindme` — delayed DM/channel reminder
- ● `/timestamp` — Discord auto-localized timestamp generator
- `/todo add`, `/todo list`, `/todo done`
- `/poll create`, `/poll close`
- `/note save`, `/note list`
- `/schedule`, `/standup`, `/timer`, `/countdown`
- Suggested split: `cogs/productivity/todos.py`, `cogs/productivity/polls.py`,
  `cogs/productivity/scheduling.py`.

## Fun (`cogs/fun/`)
- ● `/coinflip`, `/roll`, `/8ball`
- `/meme`, `/joke`, `/trivia`, `/wouldyourather`
- `/rps` (rock-paper-scissors), `/tictactoe`, `/hangman`
- `/rank`, `/leaderboard` (XP/leveling)
- Suggested split: `cogs/fun/games.py` (already started),
  `cogs/fun/leveling.py`, `cogs/fun/social.py`.

## How to add the remaining commands

1. Pick the category directory the command belongs in.
2. Create (or extend) a `.py` file there following the same shape as
   the existing examples: a `commands.Cog` subclass with
   `@app_commands.command(...)` methods, plus a module-level
   `async def setup(bot): await bot.add_cog(...)`.
3. Deploy. `setup_hook()` in `main.py` re-scans `cogs/` on every boot
   and will pick the new file up with no other code changes.
4. Keep each file focused (roughly 3–8 related commands) rather than
   one giant file per category — this keeps hot-reloads (`/reload`)
   fast and narrow, and keeps failures in one file from blocking
   the rest of that category from loading (each extension load is
   isolated and reported separately — see `stats.failed_extensions`
   on the dashboard).
