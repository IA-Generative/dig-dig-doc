<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import ActivityModal from "@/components/dashboard/ActivityModal.vue";
import AgendaToolbar, { type AgendaView } from "@/components/dashboard/AgendaToolbar.vue";
import DashboardHeader from "@/components/dashboard/DashboardHeader.vue";
import MetricsRow from "@/components/dashboard/MetricsRow.vue";
import NotificationsModal from "@/components/dashboard/NotificationsModal.vue";
import UnassignedModal from "@/components/dashboard/UnassignedModal.vue";
import UrgencyCalendar from "@/components/dashboard/UrgencyCalendar.vue";
import UrgencyFilters from "@/components/dashboard/UrgencyFilters.vue";
import UrgencyListView from "@/components/dashboard/UrgencyListView.vue";
import { useDashboard } from "@/composables/useDashboard";
import { useNotifications } from "@/composables/useNotifications";
import { useUrgencyFilters } from "@/composables/useUrgencyFilters";
import type { SlotDraft } from "@/types/schedule";

// Page = simple assemblage : chaque bloc vit dans son propre composant
// (components/dashboard/…), les données dans useDashboard / useNotifications.

const { data, loading, error, fetchDashboard, setSchedule } = useDashboard();
const { unreadCount, setReminders } = useNotifications();

onMounted(fetchDashboard);

// La journée est la vue par défaut : c'est l'agenda du jour.
const view = ref<AgendaView>("day");
const filtersOpen = ref(false);
const notifOpen = ref(false);
const unassignedOpen = ref(false);
const activityOpen = ref(false);

const urgencies = computed(() => data.value?.urgencies ?? []);
const { search, dueFilter, analyseFilter, sorted, analyseOptions, searched, filtered, hasActiveFilters, reset } =
  useUrgencyFilters(urgencies, computed(() => view.value === "list"));

/** Enregistre le créneau d'un dossier puis (re)programme ses rappels. */
function onSchedule(dossierId: string, slot: SlotDraft | null) {
  setSchedule(dossierId, slot);
  const name = urgencies.value.find((u) => u.dossierId === dossierId)?.dossierName ?? "";
  setReminders(dossierId, name, slot);
}
</script>

<template>
  <div class="dashboard">
    <DashboardHeader
      :unread-count="unreadCount"
      :unassigned-count="data?.unassigned?.length ?? null"
      @open-notifications="notifOpen = true"
      @open-unassigned="unassignedOpen = true"
      @open-activity="activityOpen = true"
    />

    <p v-if="loading" class="dashboard__state" role="status">
      <VIcon name="ri-loader-4-line" class="dashboard__spinner" /> Chargement…
    </p>

    <div v-else-if="error" class="fr-alert fr-alert--error" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary fr-mt-1w" @click="fetchDashboard">
        Réessayer
      </button>
    </div>

    <template v-else-if="data">
      <!-- Quatre indicateurs simples ; le détail s'ouvre au clic. -->
      <MetricsRow :urgencies="sorted" :stats="data.stats" :status-counts="data.statusCounts" />

      <h2 class="dashboard__agenda-title">Mon agenda</h2>
      <AgendaToolbar v-model:view="view" v-model:filters-open="filtersOpen" :filters-active="hasActiveFilters" />

      <UrgencyFilters
        v-if="filtersOpen"
        v-model:search="search"
        v-model:due-filter="dueFilter"
        v-model:analyse-filter="analyseFilter"
        :analyse-options="analyseOptions"
        :show-due="view === 'list'"
        :has-active-filters="hasActiveFilters"
        @reset="reset"
      />

      <UrgencyListView
        v-if="view === 'list'"
        :urgencies="filtered"
        :no-urgency-at-all="sorted.length === 0"
        @schedule="onSchedule"
      />
      <UrgencyCalendar v-else v-model:view="view" :urgencies="searched" @schedule="onSchedule" />
    </template>

    <NotificationsModal v-if="notifOpen" @close="notifOpen = false" />
    <UnassignedModal v-if="unassignedOpen && data?.unassigned" :items="data.unassigned" @close="unassignedOpen = false" />
    <ActivityModal v-if="activityOpen && data" :items="data.activity" @close="activityOpen = false" />
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 56rem;
  margin: 0 auto;
}

.dashboard__state {
  color: var(--text-mention-grey);
}

.dashboard__spinner {
  animation: dashboard-spin 1s linear infinite;
}

@keyframes dashboard-spin {
  to {
    transform: rotate(360deg);
  }
}

.dashboard__agenda-title {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  font-weight: 800;
}
</style>
