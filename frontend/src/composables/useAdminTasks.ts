import { ref } from "vue";

import { apiFetch } from "@/utils/api";
import type { AdminTasks } from "@/types/admin";

/** Introspection des tâches Celery (page Administration). */
export function useAdminTasks() {
  const tasks = ref<AdminTasks | null>(null);
  const loading = ref(false);
  const error = ref("");

  const fetchTasks = async () => {
    loading.value = true;
    error.value = "";
    try {
      tasks.value = await apiFetch<AdminTasks>("/api/admin/tasks");
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Erreur lors du chargement des tâches.";
      tasks.value = null;
    } finally {
      loading.value = false;
    }
  };

  return { tasks, loading, error, fetchTasks };
}
