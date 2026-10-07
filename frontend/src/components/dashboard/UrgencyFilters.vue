<script setup lang="ts">
import { DUE_FILTER_OPTIONS, type DueFilter } from "@/composables/useUrgencyFilters";

// Recherche + filtres de l'agenda. Le filtre d'échéance n'a de sens que
// dans la vue liste (`showDue`).
const search = defineModel<string>("search", { required: true });
const dueFilter = defineModel<DueFilter>("dueFilter", { required: true });
const analyseFilter = defineModel<string>("analyseFilter", { required: true });

defineProps<{
  analyseOptions: { value: string; text: string }[];
  showDue: boolean;
  hasActiveFilters: boolean;
}>();
defineEmits<{ reset: [] }>();
</script>

<template>
  <div id="dash-filters" class="filters" role="search">
    <DsfrInput v-model="search" label="Rechercher" label-visible placeholder="Dossier, analyse, statut…" type="search" />
    <DsfrSelect v-if="showDue" v-model="dueFilter" label="Échéance" label-visible :options="DUE_FILTER_OPTIONS" />
    <DsfrSelect v-model="analyseFilter" label="Analyse" label-visible :options="analyseOptions" />
    <button v-if="hasActiveFilters" type="button" class="filters__reset" @click="$emit('reset')">Réinitialiser</button>
  </div>
</template>

<style scoped>
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  align-items: end;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.filters :deep(.fr-input-group),
.filters :deep(.fr-select-group) {
  margin-bottom: 0;
}

.filters__reset {
  justify-self: start;
  padding: 0;
  border: none;
  background: none;
  color: var(--text-action-high-blue-france);
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
</style>
