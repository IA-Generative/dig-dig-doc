import { computed, ref } from "vue";

import type { Version } from "@/types/analyse";
import {
  type Assignee,
  type ColumnId,
  type CustomField,
  type CustomValue,
  type TrackingFilters,
  type TrackingRow,
  type TrackingSort,
  type TrackingStatus,
} from "@/types/tracking";
import { useDossierAccess } from "@/composables/useDossierAccess";
import { expiryInfo } from "@/utils/expiry";
import { matchesFieldFilter, validateValue } from "@/utils/trackingFields";

// MOCK (issue #173, partie UI) : état partagé au niveau du module, à
// remplacer par l'API (affectations, statuts #168, péremption #172, champs
// personnalisés). Les signatures de `query` / `assign` / `setValue` suivent
// ce que fera l'API : filtres, tri et pagination côté serveur.

export const ME = "u1";

export const ASSIGNEES: Assignee[] = [
  { id: "u1", name: "Alex Martin" },
  { id: "u2", name: "Camille Durand" },
  { id: "u3", name: "Samir Benali" },
  { id: "u4", name: "Léa Petit" },
  { id: "u5", name: "Noah Roux" },
];

export const STATUSES: TrackingStatus[] = [
  { id: "a_instruire", label: "À instruire", tone: "new", final: false },
  { id: "en_instruction", label: "En instruction", tone: "info", final: false },
  { id: "pieces_manquantes", label: "Pièces manquantes", tone: "warning", final: false },
  { id: "a_valider", label: "À valider", tone: "new", final: false },
  { id: "clos", label: "Clos", tone: "success", final: true },
];

const daysFromNow = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString();
const SERVICES = ["Culture", "Sport", "Social", "Éducation"];

function initialFields(): CustomField[] {
  return [
    { id: "f_montant", name: "Montant demandé", definition: "Montant de l'aide sollicité par le demandeur, tel qu'indiqué dans le formulaire.", type: "amount", required: false, defaultValue: null, choices: [], currency: "EUR" },
    { id: "f_service", name: "Service", definition: "Service instructeur en charge du dossier.", type: "choice", required: true, defaultValue: "Culture", choices: SERVICES, currency: "EUR" },
    { id: "f_depot", name: "Date de dépôt", definition: "Date de réception du dossier complet. Sert de point de départ au délai d'instruction.", type: "date", required: false, defaultValue: null, choices: [], currency: "EUR" },
    { id: "f_prioritaire", name: "Prioritaire", definition: "À cocher quand le dossier doit être traité avant les autres.", type: "boolean", required: false, defaultValue: false, choices: [], currency: "EUR" },
  ];
}

function initialRows(): TrackingRow[] {
  return Array.from({ length: 42 }, (_, i) => ({
    id: `trk-${i + 1}`,
    reference: `DOS-2026-${String(i + 1).padStart(4, "0")}`,
    statusId: STATUSES[i % STATUSES.length].id,
    assigneeId: i % 4 === 3 ? null : ASSIGNEES[i % ASSIGNEES.length].id,
    expiresAt: i % 9 === 8 ? null : daysFromNow(((i * 7) % 70) - 8),
    createdAt: daysFromNow(-60 + i),
    lastActivityAt: daysFromNow(-((i * 3) % 20)),
    values: {
      f_montant: i % 5 === 4 ? null : 1000 + ((i * 937) % 24000),
      f_service: SERVICES[i % SERVICES.length],
      f_depot: daysFromNow(-70 + i).slice(0, 10),
      f_prioritaire: i % 6 === 0,
    },
  }));
}

const rows = ref<TrackingRow[]>(initialRows());
const fields = ref<CustomField[]>(initialFields());
const fieldsVersions = ref<Version<CustomField[]>[]>([]);
/** Journal local simulant l'historique du dossier (#169) : affectations et valeurs modifiées. */
const log = ref<string[]>([]);

let versionSeq = 1;
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

const statusOrder = (id: string) => STATUSES.findIndex((s) => s.id === id);
const assigneeName = (id: string | null) => ASSIGNEES.find((a) => a.id === id)?.name ?? "";

const accessApi = useDossierAccess();

function matches(row: TrackingRow, f: TrackingFilters): boolean {
  // Visibilité (#177) : un dossier inaccessible n'apparaît jamais (ni dans les compteurs ni dans l'export).
  if (!accessApi.canSee(row.id)) return false;
  if (f.access && accessApi.accessOf(row.id).visibility !== f.access) return false;
  if (f.statusId && row.statusId !== f.statusId) return false;
  if (f.assignee === "me" && row.assigneeId !== ME) return false;
  if (f.assignee === "none" && row.assigneeId !== null) return false;
  if (f.assignee && f.assignee !== "me" && f.assignee !== "none" && row.assigneeId !== f.assignee) return false;
  if (f.due) {
    const { days } = expiryInfo(row.expiresAt);
    if (f.due === "none" && row.expiresAt !== null) return false;
    if (f.due === "expired" && !(days !== null && days < 0)) return false;
    if ((f.due === "7" || f.due === "30") && !(days !== null && days >= 0 && days <= Number(f.due))) return false;
  }
  const query = f.search.trim().toLowerCase();
  if (query) {
    const haystack = [row.reference, ...Object.values(row.values).map(String)].join(" ").toLowerCase();
    if (!haystack.includes(query)) return false;
  }
  for (const [fieldId, filter] of Object.entries(f.fieldFilters)) {
    const field = fields.value.find((x) => x.id === fieldId);
    if (field && !matchesFieldFilter(field, row.values[fieldId], filter)) return false;
  }
  return true;
}

function sortValue(row: TrackingRow, key: ColumnId): string | number {
  switch (key) {
    case "reference":
      return row.reference;
    case "status":
      return statusOrder(row.statusId);
    case "assignee":
      return assigneeName(row.assigneeId) || "￿"; // les non affectés en dernier
    case "expiry":
      return row.expiresAt ? Date.parse(row.expiresAt) : Infinity;
    case "createdAt":
      return Date.parse(row.createdAt);
    case "lastActivityAt":
      return Date.parse(row.lastActivityAt);
    default: {
      const v = row.values[key.slice("field:".length)];
      return typeof v === "number" ? v : String(v ?? "");
    }
  }
}

function filteredSorted(filters: TrackingFilters, sort: TrackingSort): TrackingRow[] {
  const dir = sort.dir === "asc" ? 1 : -1;
  return rows.value
    .filter((r) => matches(r, filters))
    .sort((a, b) => {
      const x = sortValue(a, sort.key);
      const y = sortValue(b, sort.key);
      return (x < y ? -1 : x > y ? 1 : 0) * dir;
    });
}

export function useTracking() {
  /** Équivalent de l'appel API paginé : filtres, tri et pagination côté « serveur ». */
  async function query(filters: TrackingFilters, sort: TrackingSort, page: number, pageSize: number) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const all = filteredSorted(filters, sort);
    return { rows: all.slice((page - 1) * pageSize, page * pageSize).map(clone), total: all.length };
  }

  /** Toutes les lignes de la vue (export CSV). */
  function queryAll(filters: TrackingFilters, sort: TrackingSort): TrackingRow[] {
    return filteredSorted(filters, sort).map(clone);
  }

  /** Affecte (ou désaffecte, avec `null`) un ou plusieurs dossiers. */
  function assign(ids: string[], assigneeId: string | null) {
    for (const row of rows.value) {
      if (!ids.includes(row.id)) continue;
      log.value.unshift(`${row.reference} : ${assigneeId ? `affecté à ${assigneeName(assigneeId)}` : "désaffecté"}`);
      row.assigneeId = assigneeId;
    }
  }

  /** Modifie une valeur personnalisée ; renvoie le message d'erreur de validation, ou `null`. */
  function setValue(rowId: string, fieldId: string, value: CustomValue): string | null {
    const field = fields.value.find((f) => f.id === fieldId);
    const row = rows.value.find((r) => r.id === rowId);
    if (!field || !row) return "Champ introuvable.";
    const error = validateValue(field, value);
    if (error) return error;
    log.value.unshift(`${row.reference} : « ${field.name} » modifié`);
    row.values[fieldId] = value;
    return null;
  }

  /** Enregistre les définitions de champs : l'état précédent est conservé dans l'historique. */
  function saveFields(next: CustomField[], purgeRemoved: boolean) {
    fieldsVersions.value.unshift({
      id: `fv-${versionSeq++}`,
      content: clone(fields.value),
      createdAt: new Date().toISOString(),
    });
    const keptIds = new Set(next.map((f) => f.id));
    if (purgeRemoved) {
      for (const row of rows.value) {
        for (const key of Object.keys(row.values)) if (!keptIds.has(key)) delete row.values[key];
      }
    }
    fields.value = clone(next);
  }

  /** Restaure une version antérieure ; l'état courant devient lui-même une version. */
  function restoreFieldsVersion(versionId: string) {
    const version = fieldsVersions.value.find((v) => v.id === versionId);
    if (!version) return;
    fieldsVersions.value.unshift({ id: `fv-${versionSeq++}`, content: clone(fields.value), createdAt: new Date().toISOString() });
    fields.value = clone(version.content);
  }

  /** Valeur par défaut d'un nouveau champ pour les dossiers existants : non rétroactive (valeur vide). */
  const statusCounts = computed(() =>
    STATUSES.map((s) => ({ ...s, count: rows.value.filter((r) => r.statusId === s.id).length })),
  );

  return {
    rows,
    fields,
    fieldsVersions,
    log,
    statuses: STATUSES,
    assignees: ASSIGNEES,
    statusCounts,
    query,
    queryAll,
    assign,
    setValue,
    saveFields,
    restoreFieldsVersion,
    assigneeName,
  };
}
