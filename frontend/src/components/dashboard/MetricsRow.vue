<script setup lang="ts">
import { computed, ref } from "vue";

import MetricCard from "@/components/dashboard/MetricCard.vue";
import MetricsDetailModal from "@/components/dashboard/MetricsDetailModal.vue";
import type { DashboardStats, DashboardStatusCount, DashboardUrgency } from "@/types/dashboard";

// Quatre indicateurs simples et neutres en haut de page. Un clic sur
// l'un d'eux ouvre le détail (MetricsDetailModal). Pour en ajouter : un
// élément dans `metrics`.
const props = defineProps<{
  urgencies: DashboardUrgency[];
  stats: DashboardStats;
  statusCounts: DashboardStatusCount[];
}>();

const detailOpen = ref(false);

const metrics = computed(() => [
  { key: "total", label: "Dossiers", value: props.stats.totalDossiers },
  { key: "planned", label: "Planifiés", value: props.urgencies.filter((u) => u.plannedStart).length },
  { key: "closed", label: "Clôturés", value: props.stats.closedDossiers },
  { key: "week", label: "Traités cette semaine", value: props.stats.completedThisWeek, tone: "success" as const },
]);
</script>

<template>
  <div class="metrics" role="group" aria-label="Mes indicateurs">
    <MetricCard
      v-for="m in metrics"
      :key="m.key"
      :label="m.label"
      :value="m.value"
      :tone="m.tone"
      interactive
      @select="detailOpen = true"
    />
  </div>

  <MetricsDetailModal
    v-if="detailOpen"
    :urgencies="urgencies"
    :stats="stats"
    :status-counts="statusCounts"
    @close="detailOpen = false"
  />
</template>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
</style>
