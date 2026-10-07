import type { DashboardUrgency } from "@/types/dashboard";
import {
  REMINDER_PRESETS,
  WEEKDAY_NAMES,
  type Recurrence,
  type SlotDraft,
} from "@/types/schedule";

/** Garde-fou : on n'énumère jamais plus d'occurrences que ça. */
const MAX_OCCURRENCES = 5000;

/** Lundi = 0 … dimanche = 6 (getDay() renvoie 0 pour dimanche). */
export const weekdayOf = (d: Date) => (d.getDay() + 6) % 7;

const daysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();

function* generate(start: Date, rec: Recurrence): Generator<Date> {
  const h = start.getHours();
  const min = start.getMinutes();
  const interval = Math.max(1, rec.interval);

  if (rec.unit === "day") {
    for (let k = 0; ; k++) {
      yield new Date(start.getFullYear(), start.getMonth(), start.getDate() + k * interval, h, min);
    }
  } else if (rec.unit === "week") {
    const days = [...(rec.weekdays?.length ? rec.weekdays : [weekdayOf(start)])].sort((a, b) => a - b);
    const mondayOffset = weekdayOf(start);
    for (let w = 0; ; w++) {
      for (const wd of days) {
        const occ = new Date(
          start.getFullYear(),
          start.getMonth(),
          start.getDate() - mondayOffset + w * interval * 7 + wd,
          h,
          min,
        );
        if (occ >= start) yield occ;
      }
    }
  } else if (rec.unit === "month") {
    for (let k = 0; ; k++) {
      const first = new Date(start.getFullYear(), start.getMonth() + k * interval, 1);
      const day = Math.min(start.getDate(), daysInMonth(first.getFullYear(), first.getMonth()));
      yield new Date(first.getFullYear(), first.getMonth(), day, h, min);
    }
  } else {
    for (let k = 0; ; k++) {
      const year = start.getFullYear() + k * interval;
      const day = Math.min(start.getDate(), daysInMonth(year, start.getMonth()));
      yield new Date(year, start.getMonth(), day, h, min);
    }
  }
}

/** Débuts d'occurrence compris entre `from` et `to` (inclus), dans l'ordre. */
export function occurrenceStarts(start: Date, rec: Recurrence | undefined, from: Date, to: Date): Date[] {
  if (!rec) return start >= from && start <= to ? [start] : [];

  let until = Infinity;
  if (rec.end.type === "until") {
    const [y, m, d] = rec.end.date.split("-").map(Number);
    until = new Date(y, m - 1, d, 23, 59, 59).getTime();
  }
  const maxCount = rec.end.type === "count" ? rec.end.count : Infinity;

  const out: Date[] = [];
  let n = 0;
  for (const occ of generate(start, rec)) {
    if (n >= maxCount || n >= MAX_OCCURRENCES || occ.getTime() > until || occ > to) break;
    n++;
    if (occ >= from) out.push(occ);
  }
  return out;
}

export function formatReminder(minutes: number): string {
  const preset = REMINDER_PRESETS.find((p) => p.value === minutes);
  if (preset) return preset.text;
  if (minutes % 1440 === 0) return `${minutes / 1440} jours avant`;
  if (minutes % 60 === 0) return `${minutes / 60} heures avant`;
  return `${minutes} minutes avant`;
}

function joinDays(days: number[]) {
  const names = days.map((d) => WEEKDAY_NAMES[d]);
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} et ${names[names.length - 1]}` : names[0];
}

/** Phrase lisible : « Toutes les 2 semaines le lundi et jeudi, jusqu'au 12 déc. 2026 ». */
export function summarizeRecurrence(rec: Recurrence, start: Date): string {
  const n = rec.interval;
  let base: string;
  if (rec.unit === "day") {
    base = n === 1 ? "Tous les jours" : `Tous les ${n} jours`;
  } else if (rec.unit === "week") {
    const days = [...(rec.weekdays?.length ? rec.weekdays : [weekdayOf(start)])].sort((a, b) => a - b);
    const everyDay = days.length === 7;
    const workdays = days.length === 5 && days.every((d, i) => d === i);
    if (n === 1 && everyDay) base = "Tous les jours";
    else if (n === 1 && workdays) base = "Tous les jours ouvrés";
    else {
      const freq = n === 1 ? "Toutes les semaines" : `Toutes les ${n} semaines`;
      base = `${freq} le ${joinDays(days)}`;
    }
  } else if (rec.unit === "month") {
    base = n === 1 ? "Tous les mois" : `Tous les ${n} mois`;
  } else {
    base = n === 1 ? "Tous les ans" : `Tous les ${n} ans`;
  }

  if (rec.end.type === "until") {
    const [y, m, d] = rec.end.date.split("-").map(Number);
    const label = new Date(y, m - 1, d).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
    return `${base}, jusqu'au ${label}`;
  }
  if (rec.end.type === "count") return `${base}, ${rec.end.count} fois`;
  return base;
}

export function summarizeReminders(reminders: number[]): string {
  return reminders.length === 0 ? "Aucun rappel" : reminders.map(formatReminder).join(", ");
}

/** Résumé complet d'un créneau, pour le haut de l'éditeur. */
export function summarizeSlot(slot: Pick<SlotDraft, "recurrence" | "reminders">, start: Date): string {
  return [
    slot.recurrence ? summarizeRecurrence(slot.recurrence, start) : "Une seule fois",
    summarizeReminders(slot.reminders),
  ].join(" · ");
}

/** Créneau d'un dossier au format de l'éditeur, ou `null` s'il n'est pas planifié. */
export function slotOfUrgency(u: DashboardUrgency): SlotDraft | null {
  return u.plannedStart && u.plannedEnd
    ? { start: u.plannedStart, end: u.plannedEnd, recurrence: u.recurrence, reminders: u.reminders ?? [] }
    : null;
}
