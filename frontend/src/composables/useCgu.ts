import { ref } from "vue";

import { apiFetch } from "@/utils/api";
import type { CguAcceptanceStatus, CguAdminVersion, CguVersion } from "@/types/cgu";

function mapCgu(api: any): CguVersion {
  return {
    id: api.id,
    content: api.content,
    version: api.version,
    publishedAt: api.published_at,
  };
}

function mapCguAdmin(api: any): CguAdminVersion {
  return {
    id: api.id,
    content: api.content,
    version: api.version,
    isActive: api.is_active,
    publishedAt: api.published_at,
    createdBy: api.created_by,
    createdAt: api.created_at,
  };
}

function mapAcceptanceStatus(api: any): CguAcceptanceStatus {
  return {
    accepted: api.accepted,
    cgu: api.cgu ? mapCgu(api.cgu) : null,
  };
}

/**
 * CGU versionnées : récupération de la version active, statut d'acceptation
 * de l'utilisateur courant, et gestion admin (création/activation/édition).
 *
 * L'état d'acceptation est partagé (singleton via module) pour que le
 * CguGate puisse bloquer l'app entière tant que l'utilisateur n'a pas
 * accepté la version active.
 */
const acceptanceStatus = ref<CguAcceptanceStatus>({ accepted: true, cgu: null });
const acceptanceLoading = ref(false);

export function useCgu() {
  /** Récupère la version active des CGU (route publique). */
  const fetchActive = async (): Promise<CguVersion | null> => {
    try {
      const data = await apiFetch<any>("/api/cgu");
      return mapCgu(data);
    } catch (error: any) {
      if (error?.status === 404) return null;
      throw error;
    }
  };

  /** Récupère le statut d'acceptation de l'utilisateur courant. */
  const fetchAcceptanceStatus = async (): Promise<CguAcceptanceStatus> => {
    acceptanceLoading.value = true;
    try {
      const data = await apiFetch<any>("/api/cgu/acceptance");
      acceptanceStatus.value = mapAcceptanceStatus(data);
      return acceptanceStatus.value;
    } finally {
      acceptanceLoading.value = false;
    }
  };

  /** Enregistre l'acceptation de la version active par l'utilisateur courant. */
  const acceptCgu = async (): Promise<CguAcceptanceStatus> => {
    const data = await apiFetch<any>("/api/cgu/acceptance", { method: "POST" });
    acceptanceStatus.value = mapAcceptanceStatus(data);
    return acceptanceStatus.value;
  };

  // ── Admin ────────────────────────────────────────────────────────────

  const versions = ref<CguAdminVersion[]>([]);

  const fetchVersions = async (): Promise<CguAdminVersion[]> => {
    const data = await apiFetch<any[]>("/api/admin/cgu/versions");
    versions.value = data.map(mapCguAdmin);
    return versions.value;
  };

  const createVersion = async (content: string): Promise<CguAdminVersion> => {
    const data = await apiFetch<any>("/api/admin/cgu", {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    return mapCguAdmin(data);
  };

  const updateVersion = async (id: string, content: string): Promise<CguAdminVersion> => {
    const data = await apiFetch<any>(`/api/admin/cgu/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    });
    return mapCguAdmin(data);
  };

  const activateVersion = async (id: string): Promise<CguAdminVersion> => {
    const data = await apiFetch<any>(`/api/admin/cgu/${id}/activate`, { method: "POST" });
    return mapCguAdmin(data);
  };

  return {
    // Acceptance (shared state)
    acceptanceStatus,
    acceptanceLoading,
    fetchActive,
    fetchAcceptanceStatus,
    acceptCgu,
    // Admin
    versions,
    fetchVersions,
    createVersion,
    updateVersion,
    activateVersion,
  };
}
