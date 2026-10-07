import { dayOffset } from "@/utils/dates";

export type ExpiryTone = "none" | "ok" | "warning" | "danger" | "expired";

// MOCK (#172) : seuils de couleur de l'analyse, en jours restants.
const THRESHOLDS = { ok: 30, warning: 7 };

/** Libellé et niveau d'une date de péremption : la couleur n'est jamais le seul signal. */
export function expiryInfo(iso: string | null): { label: string; tone: ExpiryTone; days: number | null } {
  if (!iso) return { label: "Sans date", tone: "none", days: null };
  const days = dayOffset(iso);
  if (days < 0) return { label: `Expiré depuis ${-days} j`, tone: "expired", days };
  if (days === 0) return { label: "Expire aujourd'hui", tone: "danger", days };
  const label = `Expire dans ${days} j`;
  if (days < THRESHOLDS.warning) return { label, tone: "danger", days };
  if (days <= THRESHOLDS.ok) return { label, tone: "warning", days };
  return { label, tone: "ok", days };
}
