<script setup lang="ts">
import type { WorkflowStatus } from "@/types/analyse";

// Pastille d'un statut de dossier : un point de la couleur du statut, son nom
// toujours écrit (la couleur n'est jamais le seul signal), et une coche si le
// dossier est clos dans ce statut.
defineProps<{ status: Pick<WorkflowStatus, "name" | "color" | "isFinal"> }>();
</script>

<template>
  <span class="wsb">
    <span class="wsb__dot" :style="{ background: status.color }" aria-hidden="true" />
    <span class="wsb__name">{{ status.name }}</span>
    <VIcon v-if="status.isFinal" name="ri-check-line" class="wsb__final" aria-label="Statut final : dossier clos" />
  </span>
</template>

<style scoped>
.wsb {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.125rem 0.625rem 0.125rem 0.5rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 1rem;
  background: var(--background-default-grey);
  font-size: 0.8125rem;
  font-weight: 600;
  white-space: nowrap;
}

.wsb__dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.wsb__final {
  color: var(--text-default-success);
}
</style>
