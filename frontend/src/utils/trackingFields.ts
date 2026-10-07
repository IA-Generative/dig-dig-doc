import type { CustomField, CustomValue, FieldFilter } from "@/types/tracking";

/** Erreur de validation d'une valeur selon le type du champ, ou `null` si elle est valide. */
export function validateValue(field: CustomField, value: CustomValue): string | null {
  const empty = value === null || value === "" || value === undefined;
  if (empty) return field.required && field.type !== "boolean" ? "Ce champ est obligatoire." : null;
  switch (field.type) {
    case "number":
      return typeof value === "number" && Number.isFinite(value) ? null : "Saisissez un nombre.";
    case "amount":
      return typeof value === "number" && Number.isFinite(value) && value >= 0
        ? null
        : "Saisissez un montant positif.";
    case "date":
      return typeof value === "string" && !Number.isNaN(Date.parse(value)) ? null : "Saisissez une date valide.";
    case "choice":
      return typeof value === "string" && field.choices.includes(value) ? null : "Choisissez une valeur de la liste.";
    case "boolean":
      return typeof value === "boolean" ? null : "Valeur invalide.";
    default:
      return null;
  }
}

/** Convertit la saisie brute d'un champ en valeur typée. */
export function parseInput(field: CustomField, raw: string | number): CustomValue {
  // Un <input type="number"> lié par v-model fournit déjà un nombre.
  if (typeof raw === "number") return Number.isNaN(raw) ? null : raw;
  if (raw === "") return null;
  if (field.type === "number" || field.type === "amount") {
    const n = Number(raw.replace(",", "."));
    return Number.isNaN(n) ? raw : n;
  }
  return raw;
}

export function formatValue(field: CustomField, value: CustomValue | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  switch (field.type) {
    case "amount":
      return new Intl.NumberFormat("fr-FR", { style: "currency", currency: field.currency || "EUR" }).format(Number(value));
    case "number":
      return new Intl.NumberFormat("fr-FR").format(Number(value));
    case "date":
      return new Date(String(value)).toLocaleDateString("fr-FR");
    case "boolean":
      return value ? "Oui" : "Non";
    default:
      return String(value);
  }
}

/** Une valeur passe-t-elle le filtre d'un champ ? */
export function matchesFieldFilter(field: CustomField, value: CustomValue | undefined, filter: FieldFilter): boolean {
  if (typeof filter === "string") {
    if (filter === "") return true;
    if (field.type === "boolean") return String(Boolean(value)) === filter;
    if (field.type === "choice") return value === filter;
    return String(value ?? "").toLowerCase().includes(filter.toLowerCase());
  }
  if (!filter.min && !filter.max) return true;
  if (value === null || value === undefined || value === "") return false;
  const compare = field.type === "date" ? String(value) : Number(value);
  const min = field.type === "date" ? filter.min : Number(filter.min);
  const max = field.type === "date" ? filter.max : Number(filter.max);
  return (!filter.min || compare >= min) && (!filter.max || compare <= max);
}
