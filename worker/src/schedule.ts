// Чисті функції: розбір HTML графіка, інтервали, порівняння. Без залежностей від Cloudflare.

export interface Interval {
  start: number; // хвилини від 00:00
  end: number; // 1440 = 24:00
}

export type GroupSchedule = Record<string, Interval[]>;

export interface DaySchedule {
  date: string; // DD.MM.YYYY
  groups: GroupSchedule;
}

export const ALL_GROUPS = [
  "1.1", "1.2", "2.1", "2.2", "3.1", "3.2",
  "4.1", "4.2", "5.1", "5.2", "6.1", "6.2",
];

export function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function fmt(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function formatIntervals(list: Interval[]): string {
  return list.map((i) => `${fmt(i.start)}–${fmt(i.end)}`).join(", ");
}

/** Зливає інтервали, що перетинаються або торкаються, і сортує. */
export function normalize(list: Interval[]): Interval[] {
  const sorted = list
    .filter((i) => i.end > i.start)
    .map((i) => ({ ...i }))
    .sort((a, b) => a.start - b.start);
  const out: Interval[] = [];
  for (const i of sorted) {
    const last = out[out.length - 1];
    if (last && i.start <= last.end) last.end = Math.max(last.end, i.end);
    else out.push(i);
  }
  return out;
}

/** Залишає лише частину інтервалів від `from` хвилини до кінця доби. */
export function clipFrom(list: Interval[], from: number): Interval[] {
  return normalize(
    list.map((i) => ({ start: Math.max(i.start, from), end: i.end })),
  );
}

export function sameIntervals(a: Interval[], b: Interval[]): boolean {
  return JSON.stringify(normalize(a)) === JSON.stringify(normalize(b));
}

/** Парсить текст одного рядка групи: "Електроенергії немає з 08:00 до 11:00, з 15:00 до 18:00." */
export function parseIntervals(text: string): Interval[] {
  const out: Interval[] = [];
  for (const m of text.matchAll(/з\s*(\d{1,2}:\d{2})\s*до\s*(\d{1,2}:\d{2})/g)) {
    const start = toMinutes(m[1]);
    let end = toMinutes(m[2]);
    if (end === 0) end = 1440; // "до 00:00" = кінець доби
    out.push({ start, end });
  }
  return normalize(out);
}

export function parseDay(html: string): DaySchedule | null {
  const dateMatch = html.match(/на\s+(\d{2}\.\d{2}\.\d{4})/);
  if (!dateMatch) return null;
  const groups: GroupSchedule = {};
  for (const m of html.matchAll(/Група\s+(\d+\.\d+)\.([^<]*)/g)) {
    groups[m[1]] = parseIntervals(m[2]);
  }
  if (Object.keys(groups).length === 0) return null;
  return { date: dateMatch[1], groups };
}

export interface MenuItem {
  name?: string;
  rawHtml?: string;
}

/** Відповідь API: або список меню, або (старий формат) об'єкт з hydra:member. */
export function extractItems(json: unknown): MenuItem[] {
  const members = Array.isArray(json)
    ? json
    : ((json as Record<string, unknown>)?.["hydra:member"] as unknown[]) ?? [];
  const first = members[0] as { menuItems?: MenuItem[] } | undefined;
  return first?.menuItems ?? [];
}

export function parseFeed(json: unknown): { today?: DaySchedule; tomorrow?: DaySchedule } {
  const items = extractItems(json);
  const pick = (name: string) => {
    const it = items.find((i) => i.name === name && i.rawHtml);
    return it?.rawHtml ? parseDay(it.rawHtml) ?? undefined : undefined;
  };
  return { today: pick("Today"), tomorrow: pick("Tomorrow") };
}

// ---------- Київський час ----------

export function kyivNow(now: Date = new Date()): { date: string; minutes: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Kyiv",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)!.value;
  const hour = Number(get("hour")) % 24; // деякі рушії дають "24"
  return {
    date: `${get("day")}.${get("month")}.${get("year")}`,
    minutes: hour * 60 + Number(get("minute")),
  };
}

// ---------- Порівняння ----------

/** Збережений стан: графіки за датами (макс. 2 дати). */
export type State = Record<string, GroupSchedule>;

export type Change =
  | { kind: "today"; date: string; group: string; before: Interval[]; after: Interval[] }
  | { kind: "tomorrow-new"; date: string; group: string; after: Interval[] }
  | { kind: "tomorrow-changed"; date: string; group: string; before: Interval[]; after: Interval[] };

/**
 * Порівнює новий графік зі збереженим станом.
 * - сьогодні: лише відрізок від поточної хвилини до кінця доби;
 * - завтра: повністю (новий графік або зміна).
 * Якщо стан порожній (перший запуск), змін немає.
 */
export function diffState(
  prev: State | null,
  feed: { today?: DaySchedule; tomorrow?: DaySchedule },
  nowMinutes: number,
): Change[] {
  if (!prev || Object.keys(prev).length === 0) return [];
  const changes: Change[] = [];

  const { today, tomorrow } = feed;
  if (today) {
    const old = prev[today.date];
    for (const [group, after] of Object.entries(today.groups)) {
      const before = old?.[group];
      // Дати сьогодні раніше не бачили (стан застарів) — не шумимо.
      if (!before) continue;
      if (!sameIntervals(clipFrom(before, nowMinutes), clipFrom(after, nowMinutes))) {
        changes.push({
          kind: "today",
          date: today.date,
          group,
          before: clipFrom(before, nowMinutes),
          after: clipFrom(after, nowMinutes),
        });
      }
    }
  }
  if (tomorrow) {
    const old = prev[tomorrow.date];
    for (const [group, after] of Object.entries(tomorrow.groups)) {
      const before = old?.[group];
      if (!old) {
        changes.push({ kind: "tomorrow-new", date: tomorrow.date, group, after });
      } else if (!before || !sameIntervals(before, after)) {
        changes.push({
          kind: "tomorrow-changed",
          date: tomorrow.date,
          group,
          before: before ?? [],
          after,
        });
      }
    }
  }
  return changes;
}

/** Новий стан: лише дати з поточного фіду. */
export function buildState(feed: { today?: DaySchedule; tomorrow?: DaySchedule }, prev: State | null): State {
  const next: State = {};
  for (const d of [feed.today, feed.tomorrow]) if (d) next[d.date] = d.groups;
  // Якщо одного з елементів у фіді немає, зберігаємо стару копію (на випадок тимчасового збою API).
  if (prev) {
    for (const [date, groups] of Object.entries(prev)) {
      if (!next[date] && (!feed.today || !feed.tomorrow)) next[date] = groups;
    }
  }
  return next;
}
