import { describe, expect, it } from "vitest";
import {
  buildState,
  clipFrom,
  diffState,
  extractItems,
  formatIntervals,
  kyivNow,
  parseDay,
  parseFeed,
  parseIntervals,
} from "../src/schedule";

const HTML = `<div><p><b>Графік погодинних відключень на 24.11.2026</b></p>
<p><b>Інформація станом на 20:33 24.11.2026</b></p>
<p>Група 1.1. Електроенергії немає з 08:00 до 11:00.</p>
<p>Група 2.1. Електроенергії немає з 23:30 до 24:00.</p>
<p>Група 2.2. Електроенергія є.</p>
<p>Група 4.2. Електроенергії немає з 02:00 до 03:30, з 20:00 до 21:00.</p>
</div>`;

describe("parser", () => {
  it("парсить інтервали, включно з 24:00 і кількома інтервалами", () => {
    expect(parseIntervals(" Електроенергії немає з 23:30 до 24:00.")).toEqual([{ start: 1410, end: 1440 }]);
    expect(parseIntervals(" Електроенергії немає з 02:00 до 03:30, з 20:00 до 21:00.")).toHaveLength(2);
    expect(parseIntervals(" Електроенергія є.")).toEqual([]);
  });

  it("парсить день: дата і групи", () => {
    const d = parseDay(HTML)!;
    expect(d.date).toBe("24.11.2026");
    expect(Object.keys(d.groups)).toEqual(["1.1", "2.1", "2.2", "4.2"]);
    expect(formatIntervals(d.groups["4.2"])).toBe("02:00–03:30, 20:00–21:00");
    expect(d.groups["2.2"]).toEqual([]);
  });

  it("повертає null без дати чи груп", () => {
    expect(parseDay("<p>нічого</p>")).toBeNull();
  });

  it("розуміє новий формат (список) і старий (hydra:member)", () => {
    const menu = { menuItems: [{ name: "Today", rawHtml: HTML }, { name: "Arhiv" }] };
    expect(extractItems([menu])).toHaveLength(2);
    expect(extractItems({ "hydra:member": [menu] })).toHaveLength(2);
    expect(parseFeed([menu]).today?.date).toBe("24.11.2026");
    expect(parseFeed([menu]).tomorrow).toBeUndefined();
    expect(extractItems(null)).toEqual([]);
  });
});

describe("clipFrom", () => {
  it("відрізає минулу частину", () => {
    const list = [{ start: 600, end: 840 }]; // 10:00–14:00
    expect(clipFrom(list, 720)).toEqual([{ start: 720, end: 840 }]);
    expect(clipFrom(list, 900)).toEqual([]);
    expect(clipFrom(list, 0)).toEqual(list);
  });
});

const day = (date: string, g: Record<string, [number, number][]>) => ({
  date,
  groups: Object.fromEntries(Object.entries(g).map(([k, v]) => [k, v.map(([start, end]) => ({ start, end }))])),
});

describe("diffState", () => {
  const prev = buildState(
    { today: day("24.11.2026", { "4.2": [[1200, 1260]], "1.1": [[480, 660]] }) },
    null,
  );

  it("перший запуск: без змін", () => {
    expect(diffState(null, { today: day("24.11.2026", { "4.2": [] }) }, 0)).toEqual([]);
  });

  it("зміна на сьогодні від зараз — є", () => {
    const feed = { today: day("24.11.2026", { "4.2": [[1200, 1320]], "1.1": [[480, 660]] }) };
    const ch = diffState(prev, feed, 1000);
    expect(ch).toHaveLength(1);
    expect(ch[0]).toMatchObject({ kind: "today", group: "4.2" });
  });

  it("зміна в минулих годинах — ігнорується", () => {
    const feed = { today: day("24.11.2026", { "4.2": [[1200, 1260]], "1.1": [[480, 600]] }) };
    expect(diffState(prev, feed, 1000)).toEqual([]);
  });

  it("поява графіка на завтра і його зміна", () => {
    const withTomorrow = { today: day("24.11.2026", { "4.2": [[1200, 1260]] }), tomorrow: day("25.11.2026", { "4.2": [[600, 720]] }) };
    const first = diffState(prev, withTomorrow, 1000);
    expect(first.find((c) => c.group === "4.2")).toMatchObject({ kind: "tomorrow-new" });

    const saved = buildState(withTomorrow, prev);
    const changed = { today: withTomorrow.today, tomorrow: day("25.11.2026", { "4.2": [[600, 780]] }) };
    expect(diffState(saved, changed, 1000)).toMatchObject([{ kind: "tomorrow-changed", group: "4.2" }]);
    expect(diffState(saved, withTomorrow, 1000)).toEqual([]);
  });

  it("перехід через північ: вчорашнє 'завтра' стає 'сьогодні' без сповіщень", () => {
    const saved = buildState(
      { today: day("24.11.2026", { "4.2": [] }), tomorrow: day("25.11.2026", { "4.2": [[600, 720]] }) },
      null,
    );
    const feed = { today: day("25.11.2026", { "4.2": [[600, 720]] }) };
    expect(diffState(saved, feed, 5)).toEqual([]);
  });

  it("buildState зберігає стару дату, якщо в фіді бракує Tomorrow", () => {
    const saved = buildState(
      { today: day("24.11.2026", { "4.2": [] }), tomorrow: day("25.11.2026", { "4.2": [[600, 720]] }) },
      null,
    );
    const next = buildState({ today: day("24.11.2026", { "4.2": [] }) }, saved);
    expect(Object.keys(next).sort()).toEqual(["24.11.2026", "25.11.2026"]);
  });
});

describe("kyivNow", () => {
  it("рахує київський час (зима UTC+2, літо UTC+3)", () => {
    expect(kyivNow(new Date("2026-11-24T10:30:00Z"))).toEqual({ date: "24.11.2026", minutes: 12 * 60 + 30 });
    expect(kyivNow(new Date("2026-07-01T21:30:00Z"))).toEqual({ date: "02.07.2026", minutes: 30 });
  });
});
