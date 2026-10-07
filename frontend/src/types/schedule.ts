// Planification d'un créneau de traitement : récurrence façon calendrier iOS
// et rappels multiples (issue #174, partie UI).

export type RecurrenceUnit = "day" | "week" | "month" | "year";

export type RecurrenceEnd =
  | { type: "never" }
  /** Jusqu'à ce jour inclus (YYYY-MM-DD). */
  | { type: "until"; date: string }
  | { type: "count"; count: number };

export interface Recurrence {
  unit: RecurrenceUnit;
  /** « Tous les N … » (≥ 1). */
  interval: number;
  /** Jours de la semaine concernés (0 = lundi … 6 = dimanche), pour `unit: "week"`. */
  weekdays?: number[];
  end: RecurrenceEnd;
}

/** Créneau tel qu'enregistré par l'éditeur. */
export interface SlotDraft {
  start: string;
  end: string;
  recurrence?: Recurrence;
  /** Rappels, en minutes avant chaque occurrence (0 = à l'heure). */
  reminders: number[];
}

export const MAX_REMINDERS = 3;

export const WEEKDAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];
export const WEEKDAY_INITIALS = ["L", "M", "M", "J", "V", "S", "D"];

export const REMINDER_PRESETS: { value: number; text: string }[] = [
  { value: 0, text: "À l'heure du créneau" },
  { value: 5, text: "5 minutes avant" },
  { value: 15, text: "15 minutes avant" },
  { value: 30, text: "30 minutes avant" },
  { value: 60, text: "1 heure avant" },
  { value: 120, text: "2 heures avant" },
  { value: 1440, text: "1 jour avant" },
  { value: 2880, text: "2 jours avant" },
  { value: 10080, text: "1 semaine avant" },
];

export type ReminderUnit = "minute" | "hour" | "day";

export const REMINDER_UNIT_MINUTES: Record<ReminderUnit, number> = { minute: 1, hour: 60, day: 1440 };
