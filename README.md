# LOE bot

Telegram-бот `@poweron_ukraine_bot`: графік відключень світла у Львові (Львівобленерго).

- `/queues` — вибрати черги, `/today` — графік на сьогодні й завтра, `/notify` — сповіщення по чергах.
- Кожні 5 хвилин Worker перевіряє графік і пише, якщо змінились години від зараз до кінця доби
  або з'явився/змінився графік на завтра.

Працює на Cloudflare Workers (cron + KV). Код у `worker/`, дизайн у `docs/superpowers/specs/`.

## Розробка
```bash
cd worker
npm install
npm test            # тести розбору й порівняння
npx wrangler deploy # публікація
```
Секрети (`BOT_TOKEN`, `WEBHOOK_SECRET`) задаються через `wrangler secret put`, у git їх немає.
