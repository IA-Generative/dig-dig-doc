import { apiFetch } from "@/utils/api";
import type { Assignee, ColumnId, TrackingFilters, TrackingListRow, TrackingSort } from "@/types/tracking";

// Tableau de suivi branché sur l'API (issue #173) : `GET /api/tracking` pour la liste (filtres, recherche, tri et
// pagination côté serveur), `PUT /api/dossiers/bulk-assignee` pour l'affectation, `GET /api/users` pour les
// personnes proposées. Les colonnes personnalisées et l'accès par groupe n'ont pas encore d'API : ils restent
// sur les données simulées (useTracking) ou masqués.

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Colonne de l'interface → clé de tri du serveur ; les colonnes personnalisées ne se trient pas encore. */
const SORT_KEYS: Partial<Record<ColumnId, string>> = {
  reference: "reference",
  name: "name",
  analyse: "analyse",
  status: "status",
  assignee: "assignee",
  due: "due",
  createdAt: "created_at",
  lastActivityAt: "last_activity_at",
};

/** Paramètres de la requête. Un filtre que le serveur ne connaît pas (accès, champs personnalisés) est ignoré. */
export function toQuery(filters: TrackingFilters, sort: TrackingSort, page: number, pageSize: number): URLSearchParams {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  for (const id of filters.analyseIds) query.append("analyse_id", id);
  if (filters.statusId.startsWith("cat:")) query.set("status_category", filters.statusId.slice("cat:".length));
  // Un identifiant de statut qui n'est pas un UUID vient d'un lien du tableau de bord encore simulé : on l'ignore.
  else if (UUID.test(filters.statusId)) query.set("status_id", filters.statusId);
  if (filters.assignee) query.set("assignee", filters.assignee);
  if (filters.due) query.set("due", filters.due);
  if (filters.search.trim()) query.set("search", filters.search.trim());
  query.set("sort", SORT_KEYS[sort.key] ?? "created_at");
  query.set("direction", sort.dir);
  return query;
}

function mapRow(api: any): TrackingListRow {
  return {
    id: api.id,
    reference: api.reference,
    name: api.name,
    analyse: { id: api.analyse.id, name: api.analyse.name },
    status: api.status
      ? { id: api.status.id, name: api.status.name, color: api.status.color, isFinal: api.status.is_final }
      : null,
    assignee: api.assignee ? { id: api.assignee.id, name: api.assignee.name } : null,
    dueAt: api.due_at ?? null,
    due: api.due ? { level: api.due.level, daysLeft: api.due.days_left, color: api.due.color ?? undefined } : null,
    createdAt: api.created_at,
    lastActivityAt: api.last_activity_at,
    values: {},
  };
}

interface Page {
  items: any[];
  total: number;
  pages: number;
}

/** Plafond de l'export : au-delà, le fichier est tronqué et l'interface le dit. */
export const EXPORT_LIMIT = 2000;

export function useTrackingApi() {
  async function query(filters: TrackingFilters, sort: TrackingSort, page: number, pageSize: number) {
    const data = await apiFetch<Page>(`/api/tracking?${toQuery(filters, sort, page, pageSize)}`);
    return { rows: data.items.map(mapRow), total: data.total };
  }

  /** Toutes les lignes de la vue (export CSV), par pages de 100, jusqu'à `EXPORT_LIMIT`. */
  async function queryAll(filters: TrackingFilters, sort: TrackingSort) {
    const rows: TrackingListRow[] = [];
    let total = 0;
    for (let page = 1; rows.length < EXPORT_LIMIT; page++) {
      const data = await apiFetch<Page>(`/api/tracking?${toQuery(filters, sort, page, 100)}`);
      total = data.total;
      rows.push(...data.items.map(mapRow));
      if (page >= data.pages) break;
    }
    return { rows: rows.slice(0, EXPORT_LIMIT), total };
  }

  /** Affecte (ou désaffecte, avec `null`) un ou plusieurs dossiers, en une seule transaction côté serveur. */
  async function assign(dossierIds: string[], assigneeId: string | null) {
    return apiFetch<{ updated: number; unchanged: number }>("/api/dossiers/bulk-assignee", {
      method: "PUT",
      body: JSON.stringify({ dossier_ids: dossierIds, assignee_id: assigneeId }),
    });
  }

  /** Personnes de l'annuaire proposées à l'affectation. */
  async function fetchAssignees(): Promise<Assignee[]> {
    const data = await apiFetch<{ id: string; name: string }[]>("/api/users?limit=100");
    return data.map((p) => ({ id: p.id, name: p.name }));
  }

  return { query, queryAll, assign, fetchAssignees };
}
