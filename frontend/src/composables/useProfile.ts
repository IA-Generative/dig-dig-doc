import { computed, ref } from "vue";

import { apiFetch } from "@/utils/api";
import type { UserStats } from "@/types/profile";

// Statistiques personnelles de l'utilisateur courant. Chargées à la demande
// sur la page profil (pas au démarrage de l'app - pas utile ailleurs).

const stats = ref<UserStats | null>(null);
const loading = ref(false);

export function useProfile() {
  const fetchStats = async () => {
    loading.value = true;
    try {
      stats.value = await apiFetch<UserStats>("/api/me/stats");
    } catch {
      stats.value = null;
    } finally {
      loading.value = false;
    }
  };

  return {
    stats,
    loading: computed(() => loading.value),
    fetchStats,
  };
}
;
