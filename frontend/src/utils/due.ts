import { dayOffset } from "@/utils/dates";

export type DueTone = "none" | "ok" | "warning" | "danger" | "overdue";

// MOCK (#172) : seuils de couleur de l'analyse, en jours restants.
const THRESHOLDS = { ok: 30, warning: 7 };

/** Libellé et niveau d'une date d'échéance : la couleur n'est jamais le seul signal. */
export function dueInfo(iso: string | null): { label: string; tone: DueTone; days: number | null } {
  if (!iso) return { label: "Sans échéance", tone: "none", days: null };
  const days = dayOffset(iso);
  if (days < 0) return { label: `Échéance dépassée depuis ${-days} j`, tone: "overdue", days };
  if (days === 0) return { label: "Échéance aujourd'hui", tone: "danger", days };
  const label = `Échéance dans ${days} j`;
  if (days < THRESHOLDS.warning) return { label, tone: "danger", days };
  if (days <= THRESHOLDS.ok) return { label, tone: "warning", days };
  return { label, tone: "ok", days };
}
