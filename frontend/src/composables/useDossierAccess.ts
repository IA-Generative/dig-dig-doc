import { computed } from "vue";

import { useAuth } from "@/composables/useAuth";
import type { AccessImpact, BulkAccessResult, DossierAccess, DossierAccessState } from "@/types/access";
import { apiFetch } from "@/utils/api";

// Accès aux dossiers par groupe (issue #177), branché sur l'API. La règle est appliquée par le serveur : un dossier
// qu'on ne voit pas répond 404, seuls les administrateurs modifient l'accès, et on n'associe que SES groupes (y compris
// pour un administrateur, sans appel à l'API d'administration de Keycloak).

function mapState(api: any): DossierAccessState {
  return {
    visibility: api.visibility,
    groups: api.groups.map((g: any) => g.path),
    details: api.groups.map((g: any) => ({ path: g.path, grantedBy: g.granted_by ?? null, grantedAt: g.created_at })),
    canEdit: api.can_edit,
    availableGroups: api.available_groups,
  };
}

function mapImpact(api: any): AccessImpact {
  return {
    assigneeUnassigned: api.assignee_unassigned,
    unassignedPerson: api.unassigned_person ? { id: api.unassigned_person.id, name: api.unassigned_person.name } : null,
  };
}

const body = (next: DossierAccess) => ({ visibility: next.visibility, group_paths: next.groups });

export function useDossierAccess() {
  const { profile, isAdmin } = useAuth();

  /** Les groupes de la personne connectée : les seuls qu'elle peut associer à un dossier. */
  const myGroups = computed(() => profile.value?.groups ?? []);

  async function fetchAccess(dossierId: string): Promise<DossierAccessState> {
    return mapState(await apiFetch<any>(`/api/dossiers/${dossierId}/access`));
  }

  /** Simule un changement (rien n'est enregistré) : dit si la personne affectée perdrait l'accès. */
  async function previewAccess(dossierId: string, next: DossierAccess): Promise<AccessImpact> {
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/access?dry_run=true`, {
      method: "PUT",
      body: JSON.stringify(body(next)),
    });
    return mapImpact(data);
  }

  /** Enregistre l'accès d'un dossier (administrateurs) ; le serveur trace le changement dans l'historique. */
  async function saveAccess(dossierId: string, next: DossierAccess): Promise<{ state: DossierAccessState; impact: AccessImpact }> {
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/access`, { method: "PUT", body: JSON.stringify(body(next)) });
    return { state: mapState(data), impact: mapImpact(data) };
  }

  /** Définit l'accès de plusieurs dossiers en une transaction (tout ou rien) : les groupes remplacent les actuels. */
  async function saveAccessInBulk(dossierIds: string[], next: DossierAccess): Promise<BulkAccessResult> {
    const data = await apiFetch<any>("/api/dossiers/bulk-access", {
      method: "PUT",
      body: JSON.stringify({ dossier_ids: dossierIds, ...body(next) }),
    });
    return { updated: data.updated, unchanged: data.unchanged, unassigned: data.unassigned };
  }

  return { isAdmin, myGroups, fetchAccess, previewAccess, saveAccess, saveAccessInBulk };
}
