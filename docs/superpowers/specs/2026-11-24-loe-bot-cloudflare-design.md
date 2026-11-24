# LOE bot on Cloudflare Workers — design

Status: approved in conversation (2026-11-24), short design for a small-to-medium change.

## Intent
Friends in Lviv want to see outage hours for their power queue(s) and get a Telegram
notification when the schedule changes. The old Python bot needed a running Mac and is
broken: the LOE API changed format (plain list instead of `hydra:member`).

## Goals
- Per user: choose any number of queues (1.1 … 6.2); per queue choose notifications on/off.
- Show, for each chosen queue, the outage intervals for today (and tomorrow if published).
- Background check every 5 minutes. Notify subscribers when:
  - the remainder of today (from now to 24:00) changed for their queue;
  - tomorrow's schedule was published or changed.
- Runs on Cloudflare (free tier), independent of the Mac. Multi-user (a few friends).

## Non-goals / anti-goals
- No recommendations, no comparing queues, no "hours of light left" counters.
- No notifications about hours already in the past.
- No migration of old Python bot settings. Old Python code stays until the new bot works.

## Approaches considered
1. Cloudflare Worker (webhook + Cron + KV) — chosen: free, no server, API reachable (verified).
2. Python bot on a VPS (~€4/mo) — fallback if API had blocked Cloudflare; not needed.
3. GitHub Actions cron — notifications only, no commands/buttons.
4. Own iOS app — needs Apple Developer account, APNs, server; Telegram already pushes to iPhone.

## Design
- `worker/` (TypeScript). Telegram webhook -> `fetch` handler; `scheduled` handler for cron `*/5`.
- Pure modules (unit-tested): parser, interval clipping/diff, message formatting, Kyiv time.
- Storage: one KV namespace, two keys: `users` (map chatId -> {queues, notify}) and
  `state` (last seen schedules by date, max 2 dates). KV is written only on change
  (free tier: 1000 writes/day).
- New queue added => notifications on by default; `/notify` toggles per queue (my call).
- Security: bot token and webhook secret are Cloudflare secrets, never in code/git/chat.
  Webhook requests are verified by `X-Telegram-Bot-Api-Secret-Token`.
- First run (empty state): store, do not notify. 403 from Telegram (user blocked bot): remove user.
- Time zone: Europe/Kyiv (Worker runs in UTC).
- Bot is open to anyone who finds it (my call; invite code can be added later).
