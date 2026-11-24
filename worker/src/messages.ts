import { ALL_GROUPS, Change, formatIntervals, GroupSchedule, Interval, State } from "./schedule";

export interface UserData {
  queues: string[]; // вибрані черги
  notify: string[]; // підмножина queues зі сповіщеннями
}

export type Users = Record<string, UserData>;

export function describe(list: Interval[]): string {
  return list.length ? `❌ ${formatIntervals(list)}` : "✅ світло є весь день";
}

function dayBlock(label: string, date: string, groups: GroupSchedule | undefined, queues: string[]): string {
  if (!groups) return "";
  const lines = queues.map((q) => `Черга ${q}: ${q in groups ? describe(groups[q]) : "немає даних"}`);
  return `📅 ${label} (${date})\n${lines.join("\n")}`;
}

/** Відповідь на /today: сьогодні й (якщо опубліковано) завтра. */
export function todayMessage(queues: string[], state: State | null, todayDate: string): string {
  if (queues.length === 0) return "Спочатку вибери черги: /queues";
  if (!state || Object.keys(state).length === 0) return "Графіка ще немає. Спробуй за кілька хвилин.";
  const dates = Object.keys(state);
  const toKey = (d: string) => d.split(".").reverse().join("");
  dates.sort((a, b) => toKey(a).localeCompare(toKey(b)));
  const blocks: string[] = [];
  for (const d of dates) {
    const label = d === todayDate ? "Сьогодні" : toKey(d) > toKey(todayDate) ? "Завтра" : "Раніше";
    if (label === "Раніше") continue;
    blocks.push(dayBlock(label, d, state[d], queues));
  }
  return blocks.join("\n\n") || "Графіка на сьогодні ще немає.";
}

/** Одне повідомлення зі змінами для користувача. */
export function changesMessage(changes: Change[], notify: string[]): string | null {
  const mine = changes.filter((c) => notify.includes(c.group));
  if (mine.length === 0) return null;
  const lines: string[] = [];
  const today = mine.filter((c) => c.kind === "today");
  const fresh = mine.filter((c) => c.kind === "tomorrow-new");
  const changed = mine.filter((c) => c.kind === "tomorrow-changed");

  if (today.length) {
    lines.push(`⚡ Зміни на сьогодні (${today[0].date}), від зараз до кінця доби:`);
    for (const c of today) {
      if (c.kind !== "today") continue;
      lines.push(`Черга ${c.group}: було ${c.before.length ? formatIntervals(c.before) : "світло є"} → стало ${c.after.length ? formatIntervals(c.after) : "світло є"}`);
    }
  }
  if (fresh.length) {
    if (lines.length) lines.push("");
    lines.push(`🆕 Опубліковано графік на завтра (${fresh[0].date}):`);
    for (const c of fresh) if (c.kind === "tomorrow-new") lines.push(`Черга ${c.group}: ${describe(c.after)}`);
  }
  if (changed.length) {
    if (lines.length) lines.push("");
    lines.push(`🔄 Змінився графік на завтра (${changed[0].date}):`);
    for (const c of changed) {
      if (c.kind !== "tomorrow-changed") continue;
      lines.push(`Черга ${c.group}: було ${c.before.length ? formatIntervals(c.before) : "світло є"} → стало ${c.after.length ? formatIntervals(c.after) : "світло є"}`);
    }
  }
  return lines.join("\n");
}

type Button = { text: string; callback_data: string };

export function queuesKeyboard(selected: string[]): { inline_keyboard: Button[][] } {
  const rows: Button[][] = [];
  for (let i = 0; i < ALL_GROUPS.length; i += 3) {
    rows.push(
      ALL_GROUPS.slice(i, i + 3).map((g) => ({
        text: `${selected.includes(g) ? "✅" : "▫️"} ${g}`,
        callback_data: `q:${g}`,
      })),
    );
  }
  return { inline_keyboard: rows };
}

export function notifyKeyboard(queues: string[], notify: string[]): { inline_keyboard: Button[][] } {
  const rows: Button[][] = [];
  for (let i = 0; i < queues.length; i += 3) {
    rows.push(
      queues.slice(i, i + 3).map((g) => ({
        text: `${notify.includes(g) ? "🔔" : "🔕"} ${g}`,
        callback_data: `n:${g}`,
      })),
    );
  }
  return { inline_keyboard: rows };
}

export const HELP =
  "Команди:\n" +
  "/queues — вибрати свої черги\n" +
  "/today — графік на сьогодні й завтра\n" +
  "/notify — увімкнути чи вимкнути сповіщення по чергах\n" +
  "/help — ця довідка\n\n" +
  "Я перевіряю графік Львівобленерго кожні 5 хвилин і пишу, якщо для вибраної черги змінились години на решту дня або з'явився/змінився графік на завтра.";
