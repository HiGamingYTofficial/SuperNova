# Deployment Manifest

This framework needs a host that can run a **long-lived Python process**
with an open outbound WebSocket (the Discord gateway) and an open
inbound TCP port (the dashboard/health server). That rules out purely
serverless/function-per-request platforms (they buffer one request and
return — no persistent gateway connection is possible there) and means
you want a "worker" / "background service" / VM-style Python host —
for example Railway, Render (Background Worker or Web Service), Fly.io,
a plain VPS, or Replit's "Reserved VM" always-on deployments.

## 1. Files this repo ships for deployment

```
main.py             entrypoint
web/                aiohttp dashboard + /health
cogs/                the command matrix (grows without touching main.py)
requirements.txt    pinned dependency ranges
Procfile             "web: python main.py"  (Heroku-style platforms)
runtime.txt          Python version pin
.env.example         template — copy to .env for local dev only
```

## 2. One-time Discord Developer Portal setup

1. Create an application at https://discord.com/developers/applications.
2. Under **Bot**, click "Reset Token" and copy it — this becomes
   `DISCORD_TOKEN`. Never commit it, log it, or paste it in chat/issue
   trackers.
3. Under **Bot**, enable only the privileged intents you actually need
   (Message Content / Server Members) — and set the matching
   `ENABLE_MESSAGE_CONTENT` / `ENABLE_MEMBERS_INTENT` env vars to
   `true` so the code requests them too. Both sides must agree.
4. Under **OAuth2 → General**, copy the Client ID and Client Secret for
   `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` (only needed if you
   later add an OAuth login flow to the dashboard).
5. Under **OAuth2 → URL Generator**, select the `bot` and
   `applications.commands` scopes plus whatever permissions your
   commands need, then use the generated URL to invite the bot to a
   test server (needed for the `/mod` moderation group, which only
   works in servers the bot is actually in).
6. Under **Installation**, add **User Install** to "Installation
   Contexts" (alongside or instead of Guild Install) and save. This is
   what lets *you* add the app to your own account and use the
   user-installable commands (`/text ...`, `/roleplay ...`, etc.) in
   any server or DM — no per-server invite needed for those. Then
   visit your app's install link (Installation tab has one, or use
   the URL Generator with "User Install" as the integration type) and
   click **Add to my apps**.

## 3. Environment variables (set these on the host, not in source)

| Variable | Required | Notes |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | from step 2 |
| `DISCORD_CLIENT_ID` | optional | for future OAuth features |
| `DISCORD_CLIENT_SECRET` | optional | for future OAuth features |
| `COMMAND_PREFIX` | optional | legacy text-command prefix, default `!` |
| `ENABLE_MESSAGE_CONTENT` | optional | `true`/`false`, must match Portal setting |
| `ENABLE_MEMBERS_INTENT` | optional | `true`/`false`, must match Portal setting |
| `PORT` | usually auto-set by host | the web server binds here |
| `WEB_HOST` | optional | default `0.0.0.0` |
| `DEV_GUILD_ID` | optional | instant-sync slash commands to one test guild |

## 4. Local development

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in DISCORD_TOKEN at minimum
python main.py
```

Visit `http://localhost:8080/` for the dashboard and
`http://localhost:8080/health` for the probe endpoint.

## 5. Deploying to a always-on Python host (generic worker platform)

Most platforms follow the same shape — pick the one you're using:

1. **Push this repo** to the platform (git push, CLI deploy, or
   connect a GitHub repo).
2. **Set environment variables** from the table above in the
   platform's dashboard/secrets manager — never in a committed file.
3. **Start command**: `python main.py` (already declared in
   `Procfile` for platforms that read it).
4. **Expose the port**: the platform must route external HTTP traffic
   to the port the app binds (`$PORT`, read automatically by
   `main.py`). Enable "public networking" / "expose HTTP port" if the
   platform requires an explicit toggle.
5. **Set it to always-on / no sleep**, if the platform has a toggle
   for that (some free tiers still idle after N minutes regardless).
6. **Point an external uptime pinger** (UptimeRobot, Freshping, a
   scheduled GitHub Action, etc.) at
   `https://<your-deployed-host>/health` on a 5-minute interval. This
   is the piece that actually prevents idle-timeout eviction on hosts
   that sleep inactive services — the app being "capable" of serving
   `/health` isn't enough on its own if nothing ever calls it.
7. **Confirm the bot is online** in Discord, then run `/status` in
   your test server and open the dashboard URL to confirm the gateway
   connection and web server both came up.

## 6. Process supervision / restart policy

Set the platform's restart policy to "always restart on exit" (most
have this by default for worker/service process types). `main.py`
exits cleanly on `KeyboardInterrupt` and lets any unhandled exception
propagate and crash the process on purpose — rely on the platform's
supervisor to restart it, rather than adding an internal retry-forever
loop that could mask a real configuration problem (e.g. a bad token)
behind endless silent restarts.

## 7. Scaling notes as the command matrix grows toward 300+

- Adding commands is purely a `cogs/` file-count problem — see
  `COMMAND_INDEX.md`. No deployment changes are needed as the matrix
  grows.
- If you later shard across multiple processes for a very large bot
  (thousands of guilds), each shard should run its own `main.py`
  instance; only one instance needs to expose the public dashboard —
  the rest can disable the web server or bind it to a private port.
- Discord enforces a global limit on registered application (slash)
  commands per app; if you approach it, group related commands under
  subcommand groups (`app_commands.Group`) rather than flattening
  everything at the top level.
