# How the event loop shares time between Discord and the website

Both the Discord gateway client and the aiohttp web server run as
coroutines on **one** `asyncio` event loop, inside **one** OS process.
There is no threading and no separate process for the website — that's
what lets a single free/cheap cloud instance host both. The scheduling
model is cooperative, not preemptive, which matters for understanding
where the "sharing" actually happens.

```
                         ┌─────────────────────────────┐
                         │        asyncio event loop      │
                         │   (single thread, main.py)      │
                         └──────────────┬──────────────┘
                                        │
                schedules/resumes coroutines at each await point
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
┌───────▼────────┐          ┌───────────▼───────────┐        ┌──────────▼─────────┐
│ discord.py       │          │ aiohttp web server        │        │ your cog coroutines  │
│ gateway client    │          │ (dashboard, /health,      │        │ (slash command         │
│ (WebSocket read/  │          │  /metrics)                 │        │  handlers, reminders,  │
│  write loop)      │          │                            │        │  background tasks)     │
└────────────────┘          └────────────────────────┘        └─────────────────────┘
```

## The core mechanic: cooperative multitasking

A coroutine only yields control back to the loop at an `await`. Both
subsystems here are I/O-bound, which is the case where this model
shines:

- The **gateway client** spends almost all of its time doing
  `await websocket.recv()` — waiting on network I/O from Discord.
  While it's waiting, it holds no CPU time; the loop is free to run
  something else.
- The **web server** spends almost all of its time doing
  `await reader.read()` on incoming HTTP sockets, or `await
  request_handler(...)` for the handful of milliseconds a request like
  `/health` actually takes to build a JSON response.

Because neither subsystem does long, synchronous CPU-bound work, the
loop can interleave them at a granularity of microseconds to low
milliseconds: a `/health` GET request gets fully handled in the gap
between two Discord heartbeat/read cycles, and vice versa. Neither one
"blocks" the other in the way two truly parallel, CPU-bound workloads
would need separate threads or processes to avoid blocking each other.

## Why they can be started together safely

In `main.py`, `run_web_app()` starts the aiohttp `TCPSite` **before**
`bot.start()` is awaited:

```python
web_runner = await run_web_app(web_app, host=config.web_host, port=config.web_port)
...
await bot.start(config.token)   # blocks (asynchronously) until the bot logs out
```

`web.AppRunner` + `TCPSite` bind the listening socket and return control
to the loop immediately — they don't block waiting for requests the way
`web.run_app()` would. That's the difference that makes "one server
inside another async app" possible at all: aiohttp's low-level runner
API is designed to be awaited once for setup, then left running in the
background while the loop moves on to other coroutines (here,
`bot.start`, which itself keeps yielding at every gateway read/write).

## Where this model *would* break down

If a cog handler or a web route ever did **synchronous, CPU-heavy**
work in-line — e.g. `time.sleep()` instead of `asyncio.sleep()`, a
tight non-yielding loop, heavy image processing, or a blocking network
call via a non-async HTTP library — it would starve the loop and stall
*both* subsystems for the duration, including gateway heartbeats
(risking a Discord-side disconnect) and `/health` responses (risking a
platform kill/restart, since that's the one signal your uptime pinger
relies on). Two guardrails follow directly from this:
- Only ever use `asyncio`-native or `async`-first libraries inside
  handlers (aiohttp, an async DB driver, `asyncio.sleep`, etc.).
- For any genuinely CPU-bound task, hand it to
  `loop.run_in_executor(...)` so it runs in a thread/process pool
  instead of on the event loop thread — keeping both the gateway and
  the dashboard responsive while it runs.

## Why the health check matters operationally

Free and low-cost cloud tiers commonly idle down or recycle a
container that isn't receiving any inbound traffic. `/health` exists
purely so an external pinger (UptimeRobot, Freshping, a scheduled
`curl`, or the platform's own probe) can hit the process on a fixed
interval and keep it counted as "active" — it intentionally reports
`200 OK` based on the process being alive, not on `bot.is_ready()`
being `True`, so a brief Discord-side reconnect never causes the host
to conclude the whole container is unhealthy and restart it out from
under an otherwise-fine gateway session.
