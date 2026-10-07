import { ref } from "vue";

import { ASSIGNEES, MOCK_ANALYSES, ME, STATUSES, initialDossiers, initialFieldsByAnalyse } from "@/mocks/dossiers";
import type { Version } from "@/types/analyse";
import {
  type ColumnId,
  type CustomField,
  type CustomValue,
  type TrackingFilters,
  type TrackingRow,
  type TrackingSort,
} from "@/types/tracking";
import { dueInfo } from "@/utils/due";
import { matchesFieldFilter, validateValue } from "@/utils/trackingFields";

// MOCK (issues #173 et #186, partie UI) : état partagé au niveau du module,
// à remplacer par l'API (affectations, statuts #168, échéance #172, champs
// personnalisés). Les signatures de `query` / `assign` / `setValue` suivent
// ce que fera l'API : filtres, tri et pagination côté serveur. Les dossiers
// viennent du jeu de données commun (@/mocks/dossiers), partagé avec le
// tableau de bord.

export { ASSIGNEES, ME, STATUSES };

const rows = ref<TrackingRow[]>(initialDossiers());
/** Colonnes personnalisées par analyse. */
const fieldsByAnalyse = ref<Record<string, CustomField[]>>(initialFieldsByAnalyse());
const versionsByAnalyse = ref<Record<string, Version<CustomField[]>[]>>({});
/** Journal local simulant l'historique du dossier (#169) : affectations et valeurs modifiées. */
const log = ref<string[]>([]);

let versionSeq = 1;
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

const statusOrder = (id: string) => STATUSES.findIndex((s) => s.id === id);
const assigneeName = (id: string | null) => ASSIGNEES.find((a) => a.id === id)?.name ?? "";
const analyseName = (id: string) => MOCK_ANALYSES.find((a) => a.id === id)?.name ?? id;
const allFields = () => Object.values(fieldsByAnalyse.value).flat();

function matchesStatus(row: TrackingRow, statusId: string): boolean {
  if (!statusId) return true;
  if (statusId.startsWith("cat:")) {
    return STATUSES.find((s) => s.id === row.statusId)?.category === statusId.slice("cat:".length);
  }
  return row.statusId === statusId;
}

function matches(row: TrackingRow, f: TrackingFilters): boolean {
  if (f.analyseIds.length && !f.analyseIds.includes(row.analyseId)) return false;
  if (!matchesStatus(row, f.statusId)) return false;
  if (f.assignee === "me" && row.assigneeId !== ME) return false;
  if (f.assignee === "none" && row.assigneeId !== null) return false;
  if (f.assignee && f.assignee !== "me" && f.assignee !== "none" && row.assigneeId !== f.assignee) return false;
  if (f.due) {
    const { days } = dueInfo(row.dueAt);
    if (f.due === "none" && row.dueAt !== null) return false;
    if (f.due === "overdue" && !(days !== null && days < 0)) return false;
    if ((f.due === "7" || f.due === "30") && !(days !== null && days >= 0 && days <= Number(f.due))) return false;
  }
  const query = f.search.trim().toLowerCase();
  if (query) {
    const haystack = [row.reference, row.name, ...Object.values(row.values).map(String)].join(" ").toLowerCase();
    if (!haystack.includes(query)) return false;
  }
  for (const [fieldId, filter] of Object.entries(f.fieldFilters)) {
    const field = allFields().find((x) => x.id === fieldId);
    if (field && !matchesFieldFilter(field, row.values[fieldId], filter)) return false;
  }
  return true;
}

function sortValue(row: TrackingRow, key: ColumnId): string | number {
  switch (key) {
    case "reference":
      return row.reference;
    case "name":
      return row.name;
    case "analyse":
      return analyseName(row.analyseId);
    case "status":
      return statusOrder(row.statusId);
    case "assignee":
      return assigneeName(row.assigneeId) || "￿"; // les non affectés en dernier
    case "due":
      return row.dueAt ? Date.parse(row.dueAt) : Infinity;
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
    const field = allFields().find((f) => f.id === fieldId);
    const row = rows.value.find((r) => r.id === rowId);
    if (!field || !row) return "Champ introuvable.";
    const error = validateValue(field, value);
    if (error) return error;
    log.value.unshift(`${row.reference} : « ${field.name} » modifié`);
    row.values[fieldId] = value;
    return null;
  }

  const fieldsOf = (analyseId: string): CustomField[] => fieldsByAnalyse.value[analyseId] ?? [];
  const fieldsVersionsOf = (analyseId: string): Version<CustomField[]>[] => versionsByAnalyse.value[analyseId] ?? [];

  /** Enregistre les définitions de champs d'une analyse : l'état précédent est conservé dans l'historique. */
  function saveFields(analyseId: string, next: CustomField[], purgeRemoved: boolean) {
    versionsByAnalyse.value[analyseId] = [
      { id: `fv-${versionSeq++}`, content: clone(fieldsOf(analyseId)), createdAt: new Date().toISOString() },
      ...fieldsVersionsOf(analyseId),
    ];
    const keptIds = new Set(next.map((f) => f.id));
    if (purgeRemoved) {
      for (const row of rows.value.filter((r) => r.analyseId === analyseId)) {
        for (const key of Object.keys(row.values)) if (!keptIds.has(key)) delete row.values[key];
      }
    }
    fieldsByAnalyse.value[analyseId] = clone(next);
  }

  /** Restaure une version antérieure ; l'état courant devient lui-même une version. */
  function restoreFieldsVersion(analyseId: string, versionId: string) {
    const version = fieldsVersionsOf(analyseId).find((v) => v.id === versionId);
    if (!version) return;
    versionsByAnalyse.value[analyseId] = [
      { id: `fv-${versionSeq++}`, content: clone(fieldsOf(analyseId)), createdAt: new Date().toISOString() },
      ...fieldsVersionsOf(analyseId),
    ];
    fieldsByAnalyse.value[analyseId] = clone(version.content);
  }

  return {
    rows,
    log,
    statuses: STATUSES,
    assignees: ASSIGNEES,
    analyses: MOCK_ANALYSES,
    query,
    queryAll,
    assign,
    setValue,
    fieldsOf,
    fieldsVersionsOf,
    saveFields,
    restoreFieldsVersion,
    assigneeName,
    analyseName,
  };
}
