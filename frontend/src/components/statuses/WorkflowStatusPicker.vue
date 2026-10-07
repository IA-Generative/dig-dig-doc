<script setup lang="ts">
import { computed } from "vue";

import type { WorkflowStatus } from "@/types/analyse";

// Statut d'un dossier, modifiable depuis sa vue (issue #170) : le menu propose
// les statuts de l'analyse, dans leur ordre. Un statut final clôt le dossier.
const props = defineProps<{
  /** Statuts de l'analyse du dossier. */
  statuses: WorkflowStatus[];
  current?: WorkflowStatus;
  closedAt?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ change: [statusId: string] }>();

const ordered = computed(() => [...props.statuses].sort((a, b) => a.position - b.position));
const closedLabel = computed(() =>
  props.closedAt ? new Date(props.closedAt).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) : null,
);
</script>

<template>
  <div class="wsp">
    <span v-if="current" class="wsp__dot" :style="{ background: current.color }" aria-hidden="true" />
    <label class="wsp__label">
      <span class="fr-sr-only">Changer le statut du dossier</span>
      <select class="fr-select wsp__select" :value="current?.id ?? ''" :disabled="disabled || ordered.length === 0" @change="emit('change', ($event.target as HTMLSelectElement).value)">
        <option v-if="!current" value="" disabled>Choisir un statut…</option>
        <option v-for="s in ordered" :key="s.id" :value="s.id">{{ s.name }}{{ s.isFinal ? " (final)" : "" }}</option>
      </select>
    </label>
    <span v-if="closedLabel" class="wsp__closed">Clôturé le {{ closedLabel }}</span>
  </div>
</template>

<style scoped>
.wsp {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}

.wsp__dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
}

.wsp__select {
  min-width: 12rem;
  padding: 0.25rem 2rem 0.25rem 0.5rem;
}

.wsp__closed {
  font-size: 0.8125rem;
  color: var(--text-mention-grey);
}
</style>
