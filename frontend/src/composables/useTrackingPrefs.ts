import { computed, ref, type Ref } from "vue";

import {
  NATIVE_COLUMNS,
  emptyFilters,
  type ColumnDef,
  type ColumnId,
  type ColumnPrefs,
  type CustomField,
  type TrackingFilters,
  type TrackingSort,
  type TrackingView,
} from "@/types/tracking";

// Préférences propres à l'utilisateur : vues enregistrées, colonnes visibles
// et leur ordre. MOCK : stockées dans le navigateur ; à terme côté serveur
// (par utilisateur et par analyse).

const DEFAULT_SORT: TrackingSort = { key: "due", dir: "asc" };

export const BUILT_IN_VIEWS: TrackingView[] = [
  { id: "all", name: "Tous", builtIn: true, filters: emptyFilters(), sort: DEFAULT_SORT },
  { id: "mine", name: "Mes dossiers", builtIn: true, filters: { ...emptyFilters(), assignee: "me" }, sort: DEFAULT_SORT },
  { id: "unassigned", name: "Non affectés", builtIn: true, filters: { ...emptyFilters(), assignee: "none" }, sort: { key: "createdAt", dir: "asc" } },
  { id: "soon", name: "Proches de l'échéance", builtIn: true, filters: { ...emptyFilters(), due: "7" }, sort: DEFAULT_SORT },
];

interface Stored {
  views: TrackingView[];
  columns: ColumnPrefs;
}

export function useTrackingPrefs(analyseId: Ref<string> | string, fields: Ref<CustomField[]>) {
  const key = computed(() => `digdigdoc-tracking-${typeof analyseId === "string" ? analyseId : analyseId.value}`);

  const stored = ref<Stored>({ views: [], columns: { order: [], hidden: [] } });
  try {
    const raw = localStorage.getItem(key.value);
    if (raw) stored.value = JSON.parse(raw);
  } catch {
    // Stockage indisponible : on repart des valeurs par défaut.
  }

  function persist() {
    try {
      localStorage.setItem(key.value, JSON.stringify(stored.value));
    } catch {
      // Ignoré : les préférences ne survivront pas au rechargement.
    }
  }

  const views = computed(() => [...BUILT_IN_VIEWS, ...stored.value.views]);

  function saveView(name: string, filters: TrackingFilters, sort: TrackingSort): TrackingView {
    const view: TrackingView = {
      id: `custom-${Date.now()}`,
      name: name.trim(),
      builtIn: false,
      filters: JSON.parse(JSON.stringify(filters)),
      sort: { ...sort },
    };
    stored.value.views.push(view);
    persist();
    return view;
  }

  function deleteView(id: string) {
    stored.value.views = stored.value.views.filter((v) => v.id !== id);
    persist();
  }

  /** Toutes les colonnes existantes (natives puis champs personnalisés), dans l'ordre choisi. */
  const allColumns = computed<ColumnDef[]>(() => {
    const available = [
      ...NATIVE_COLUMNS,
      ...fields.value.map((f) => ({ id: `field:${f.id}` as ColumnId, label: f.name, definition: f.definition, sortable: true })),
    ];
    const rank = (id: ColumnId) => {
      const i = stored.value.columns.order.indexOf(id);
      return i === -1 ? Infinity : i;
    };
    // Tri stable : les colonnes jamais ordonnées gardent leur ordre d'origine, à la suite.
    return [...available].sort((a, b) => rank(a.id) - rank(b.id));
  });

  const visibleColumns = computed(() => allColumns.value.filter((c) => !stored.value.columns.hidden.includes(c.id)));

  function setColumns(order: ColumnId[], hidden: ColumnId[]) {
    stored.value.columns = { order, hidden };
    persist();
  }

  function resetColumns() {
    stored.value.columns = { order: [], hidden: [] };
    persist();
  }

  return { views, saveView, deleteView, allColumns, visibleColumns, setColumns, resetColumns, hiddenColumns: computed(() => stored.value.columns.hidden) };
}
