<script setup lang="ts">
import type { DueInfo } from "@/types/dossier";
import { dueLabel } from "@/utils/due";

// Badge d'échéance (#172) : un point de la couleur du niveau (seuils de l'analyse, calculés par le serveur) et un
// libellé toujours écrit : la couleur n'est jamais le seul signal. Un dossier clos n'a plus de couleur.
defineProps<{ due: DueInfo; compact?: boolean }>();
</script>

<template>
  <span class="ddb">
    <span v-if="due.color" class="ddb__dot" :style="{ background: due.color }" aria-hidden="true" />
    <VIcon v-else name="ri-check-line" class="ddb__closed" aria-hidden="true" />
    <span class="ddb__label">{{ dueLabel(due, compact) }}</span>
  </span>
</template>

<style scoped>
.ddb {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem 0.25rem 0.5rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 1rem;
  background: var(--background-default-grey);
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.25;
}

.ddb__dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.ddb__closed {
  color: var(--text-mention-grey);
}
</style>
