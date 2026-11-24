import {
  buildState,
  diffState,
  kyivNow,
  parseFeed,
  State,
  ALL_GROUPS,
} from "./schedule";
import {
  changesMessage,
  HELP,
  notifyKeyboard,
  queuesKeyboard,
  todayMessage,
  Users,
} from "./messages";

export interface Env {
  LOE_KV: KVNamespace;
  BOT_TOKEN: string;
  WEBHOOK_SECRET: string;
}

const API_URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic";

// ---------- Telegram ----------

async function tg(env: Env, method: string, body: unknown): Promise<{ ok: boolean; error_code?: number }> {
  const res = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return (await res.json()) as { ok: boolean; error_code?: number };
}

const send = (env: Env, chatId: number | string, text: string, reply_markup?: unknown) =>
  tg(env, "sendMessage", { chat_id: chatId, text, reply_markup });

// ---------- Сховище ----------

const getUsers = async (env: Env): Promise<Users> => (await env.LOE_KV.get<Users>("users", "json")) ?? {};
const putUsers = (env: Env, u: Users) => env.LOE_KV.put("users", JSON.stringify(u));
const getState = (env: Env) => env.LOE_KV.get<State>("state", "json");

async function fetchFeed() {
  const res = await fetch(API_URL, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error(`LOE API ${res.status}`);
  return parseFeed(await res.json());
}

// ---------- Обробка повідомлень ----------

interface Update {
  message?: { chat: { id: number }; text?: string };
  callback_query?: { id: string; data?: string; message?: { chat: { id: number }; message_id: number } };
}

async function handleUpdate(env: Env, u: Update) {
  if (u.message?.text) {
    const chatId = u.message.chat.id;
    const cmd = u.message.text.trim().split(/[\s@]/)[0].toLowerCase();
    const users = await getUsers(env);
    const me = users[chatId] ?? { queues: [], notify: [] };

    if (cmd === "/start") {
      await send(env, chatId, "Привіт! Я стежу за графіком відключень світла у Львові.\nСпочатку вибери свої черги:", queuesKeyboard(me.queues));
    } else if (cmd === "/queues") {
      await send(env, chatId, "Вибери черги (натисни ще раз, щоб прибрати):", queuesKeyboard(me.queues));
    } else if (cmd === "/notify") {
      if (me.queues.length === 0) await send(env, chatId, "Спочатку вибери черги: /queues");
      else await send(env, chatId, "Сповіщення по чергах (🔔 увімкнено, 🔕 вимкнено):", notifyKeyboard(me.queues, me.notify));
    } else if (cmd === "/today") {
      let state = await getState(env);
      if (!state) {
        try {
          const feed = await fetchFeed();
          state = buildState(feed, null);
        } catch {
          return send(env, chatId, "Не вдалося отримати дані від Львівобленерго. Спробуй пізніше.");
        }
      }
      await send(env, chatId, todayMessage(me.queues, state, kyivNow().date));
    } else {
      await send(env, chatId, HELP);
    }
    return;
  }

  const cb = u.callback_query;
  if (cb?.data && cb.message) {
    const chatId = cb.message.chat.id;
    const [kind, group] = cb.data.split(":");
    if (!ALL_GROUPS.includes(group) || (kind !== "q" && kind !== "n")) {
      return tg(env, "answerCallbackQuery", { callback_query_id: cb.id });
    }
    const users = await getUsers(env);
    const me = users[chatId] ?? { queues: [], notify: [] };

    if (kind === "q") {
      if (me.queues.includes(group)) {
        me.queues = me.queues.filter((g) => g !== group);
        me.notify = me.notify.filter((g) => g !== group);
      } else {
        me.queues = ALL_GROUPS.filter((g) => me.queues.includes(g) || g === group);
        me.notify = [...me.notify, group]; // за замовчуванням сповіщення увімкнені
      }
    } else if (me.queues.includes(group)) {
      me.notify = me.notify.includes(group) ? me.notify.filter((g) => g !== group) : [...me.notify, group];
    }
    users[chatId] = me;
    await putUsers(env, users);

    await tg(env, "answerCallbackQuery", { callback_query_id: cb.id });
    await tg(env, "editMessageReplyMarkup", {
      chat_id: chatId,
      message_id: cb.message.message_id,
      reply_markup: kind === "q" ? queuesKeyboard(me.queues) : notifyKeyboard(me.queues, me.notify),
    });
  }
}

// ---------- Фонова перевірка ----------

async function check(env: Env) {
  const feed = await fetchFeed();
  if (!feed.today && !feed.tomorrow) return; // нічого не прийшло, не чіпаємо стан

  const prev = await getState(env);
  const now = kyivNow();
  const changes = diffState(prev, feed, now.minutes);
  const next = buildState(feed, prev);

  if (changes.length) {
    const users = await getUsers(env);
    let usersDirty = false;
    for (const [id, user] of Object.entries(users)) {
      const text = changesMessage(changes, user.notify);
      if (!text) continue;
      const r = await send(env, id, text);
      if (!r.ok && (r.error_code === 403 || r.error_code === 400)) {
        delete users[id]; // користувач заблокував бота чи чат недоступний
        usersDirty = true;
      }
    }
    if (usersDirty) await putUsers(env, users);
  }

  if (JSON.stringify(prev) !== JSON.stringify(next)) {
    await env.LOE_KV.put("state", JSON.stringify(next));
  }
}

// ---------- Точки входу ----------

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(req.url);
    if (req.method !== "POST" || url.pathname !== "/webhook") return new Response("ok");
    if (req.headers.get("x-telegram-bot-api-secret-token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }
    const update = (await req.json()) as Update;
    ctx.waitUntil(handleUpdate(env, update).catch((e) => console.error("update failed", e)));
    return new Response("ok");
  },

  async scheduled(_ev: ScheduledController, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(check(env).catch((e) => console.error("check failed", e)));
  },
};
